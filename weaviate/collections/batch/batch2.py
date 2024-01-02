import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, Sequence, List, Any

from pydantic import ValidationError
from requests import ReadTimeout
from requests.exceptions import HTTPError as RequestsHTTPError

from weaviate.cluster import Cluster
from weaviate.collections.batch import _BatchREST
from weaviate.collections.batch.base import ObjectsBatchRequest, ReferencesBatchRequest
from weaviate.collections.batch.grpc import _BatchGRPC
from weaviate.collections.classes.batch import (
    BatchObject,
    _BatchObject,
    _BatchReference,
    BatchReference,
    ErrorReference,
    BatchReferenceReturn,
    ErrorObject,
    BatchResult,
    BatchObjectReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.types import WeaviateField
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateBatchValidationError
from weaviate.types import UUID
from weaviate.warnings import _Warnings


class BatchExecutor(ThreadPoolExecutor):
    """
    Weaviate Batch Executor to run batch requests in separate thread.

    This class implements an additional method `_is_shutdown` that is used by the context manager.
    """

    def _is_shutdown(self) -> bool:
        return self._shutdown


class _Batch2Object:
    def __init__(
        self, connection: Connection, consistency_level: Optional[ConsistencyLevel]
    ) -> None:
        self.__connection = connection
        self.__batch_grpc = _BatchGRPC(connection, consistency_level)
        self.__batch_rest = _BatchREST(connection, consistency_level)

        # these are threadsafe as locking happens in them
        self.__batch_objects = ObjectsBatchRequest()
        self.__batch_references = ReferencesBatchRequest()

        self.__result: BatchResult = BatchResult()
        self.__failed_objects: List[ErrorObject] = []
        self.__failed_references: List[ErrorReference] = []
        self.__results_lock = threading.Lock()

        # self.__retry_failed_objects: bool = False
        # self.__retry_failed_references: bool = False

        self.__connection = connection
        self.__cluster = Cluster(self.__connection)

        self.__batch_objects = ObjectsBatchRequest()

        self._max_batch_size: int = 1000

        self._recommended_num_objects: int = 10

        # there seems to be a bug with weaviate when sending >= refs at once
        self._recommended_num_refs: int = 50

        self.__num_workers: int = 2
        self._active_threads = 0
        self._active_thread_lock = threading.Lock()
        self._last_scale_up: float = 0
        self._max_observed_rate: int = 0

        self.__start_bg_thread()

    def add_object(
        self,
        collection: str,
        properties: Optional[Dict[str, WeaviateField]],
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
        tenant: Optional[str] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Arguments:
            `collection`
                The name of the collection this object belongs to.
            `properties`
                The data properties of the object to be added as a dictionary.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            `vector`:
                The embedding of the object that should be validated. Can be used when a collection does not have a vectorization module or the given vector was generated using the _identical_ vectorization module that is configured for the class. In this case this vector takes precedence. Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
            `tenant`
                Name of the tenant.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        try:
            batch_object = BatchObject(
                collection=collection,
                properties=properties,
                uuid=uuid,
                vector=vector,
                tenant=tenant,
            )
            # self.__imported_shards.add(Shard(collection=collection, tenant=tenant))
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__batch_objects.add(batch_object._to_internal())

        # block if queue gets too long or weaviate is overloaded - reading files is faster them sending them so we do
        # not need a long queue
        if len(self.__batch_objects) >= self._recommended_num_objects * 10:
            while self._recommended_num_objects == 0:
                time.sleep(1)  # block if weaviate is overloaded

        assert batch_object.uuid is not None
        return batch_object.uuid

    def add_reference(
        self,
        from_object_uuid: UUID,
        from_object_collection: str,
        from_property_name: str,
        to_object_uuid: UUID,
        to_object_collection: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """
        Add one reference to this batch.

        Arguments:
            `from_object_uuid`
                The UUID of the object, as an uuid.UUID object or str, that should reference another object.
                It can be a Weaviate beacon or Weaviate href.
            `from_object_collection`
                The name of the collection that should reference another object.
            `from_property_name`
                The name of the property that contains the reference.
            `to_object_uuid`
                The UUID of the object, as an uuid.UUID object or str, that is actually referenced.
                It can be a Weaviate beacon or Weaviate href.
            `to_object_collection`
                The referenced object collection to which to add the reference (with UUID `to_object_uuid`).
            `tenant`
                Name of the tenant.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        try:
            batch_reference = BatchReference(
                from_object_collection=from_object_collection,
                from_object_uuid=from_object_uuid,
                from_property_name=from_property_name,
                to_object_collection=to_object_collection,
                to_object_uuid=to_object_uuid,
                tenant=tenant,
            )
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__batch_references.add(batch_reference._to_internal())

        # block if queue gets too long or weaviate is overloaded
        if (
            len(self.__batch_references) >= self._recommended_num_refs
            or self._recommended_num_objects == 0
        ):
            while self._recommended_num_objects == 0:
                time.sleep(1)  # block if weaviate is overloaded, also do not send any refs

    def __send_batch_in_bg(self, objs: List[_BatchObject], refs: List[_BatchReference]) -> None:
        if len(objs) > 0:
            start = time.time()
            try:
                response_obj = self.__batch_grpc.objects(objects=objs)
            except Exception as e:
                print(repr(e), objs)
                errors_obj = {
                    idx: ErrorObject(message=repr(e), object_=obj) for idx, obj in enumerate(objs)
                }
                response_obj = BatchObjectReturn(
                    all_responses=list(errors_obj.values()),
                    elapsed_seconds=time.time() - start,
                    errors=errors_obj,
                    has_errors=True,
                    uuids={},
                )
            self.__results_lock.acquire()
            self.__result.objs += response_obj
            self.__failed_objects.extend(response_obj.errors.values())
            self.__results_lock.release()

        if len(refs) > 0:
            start = time.time()
            try:
                response_ref = self.__batch_rest.references(references=refs)

            except Exception as e:
                print(repr(e), refs)
                errors_ref = {
                    idx: ErrorReference(message=repr(e), reference=ref)
                    for idx, ref in enumerate(refs)
                }
                response_ref = BatchReferenceReturn(
                    elapsed_seconds=time.time() - start,
                    errors=errors_ref,
                    has_errors=True,
                )
            self.__results_lock.acquire()
            self.__result.refs += response_ref
            self.__failed_references.extend(response_ref.errors.values())
            self.__results_lock.release()

        self._active_thread_lock.acquire()
        self._active_threads -= 1
        self._active_thread_lock.release()

    def flush(self) -> None:
        # bg thread is sending objs+refs automatically, so simply wait for everything to be done
        while (
            self._active_threads > 0
            or len(self.__batch_objects) > 0
            or len(self.__batch_references) > 0
        ):
            time.sleep(0.1)

        # we are done, shut bg thread down
        self.__shut_background_thread_down.set()

    def __start_bg_thread(self) -> None:
        """Create a background process that periodically checks how congested the batch queue is."""
        self.__shut_background_thread_down = threading.Event()

        def periodic_check() -> None:
            while (
                self.__shut_background_thread_down is not None
                and not self.__shut_background_thread_down.is_set()
            ):
                try:
                    status = self.__cluster.get_nodes_status()
                    if (
                        "batchStats" not in status[0]
                        or "ratePerSecond" not in status[0]["batchStats"]
                    ):
                        self.__dynamic_batching = False
                        return
                    rate = status[0]["batchStats"]["ratePerSecond"]
                    rate_per_worker = rate / self.__num_workers
                    batch_length = status[0]["batchStats"]["queueLength"]

                    if rate > self._max_observed_rate:
                        self._max_observed_rate = rate

                    if batch_length == 0:  # scale up if queue is empty
                        self._recommended_num_objects = min(
                            self._recommended_num_objects + 50,
                            self._max_batch_size,
                        )

                        if (
                            self._max_batch_size == self._recommended_num_objects
                            and time.time() - self._last_scale_up > 1
                        ):
                            self.__num_workers += 1
                            self._last_scale_up = time.time()
                        # print(
                        #     "Empty queue",
                        #     self._recommended_num_objects,
                        #     self.__num_workers,
                        #     time.time() - self._last_scale_up,
                        # )
                    else:
                        ratio = batch_length / rate
                        if (
                            2.1 > ratio > 1.9
                        ):  # ideal, send exactly as many objects as weaviate can process
                            self._recommended_num_objects = math.floor(rate_per_worker)
                        elif ratio <= 1.9:  # we can send more
                            self._recommended_num_objects = math.floor(
                                min(
                                    self._recommended_num_objects * 1.5,
                                    rate_per_worker * 2 / ratio,
                                )
                            )

                            if self._max_batch_size == self._recommended_num_objects:
                                self.__num_workers += 1

                        elif ratio < 10:  # too high, scale down
                            self._recommended_num_objects = math.floor(rate_per_worker * 2 / ratio)

                            if self._recommended_num_objects < 100 and self.__num_workers > 2:
                                self.__num_workers -= 1

                        else:  # way too high, stop sending new batches
                            # print("OVERLOAD", ratio, batch_length)
                            self._recommended_num_objects = 0
                            self.__num_workers = 2

                        # print(
                        #     "Filled queue",
                        #     self._recommended_num_objects,
                        #     self.__num_workers,
                        #     rate_per_worker,
                        #     ratio,
                        #     batch_length,
                        # )

                    # # check that we do not exceed the maximum observed rate too much. Especially important after scaling up workers
                    # if (
                    #     self._recommended_num_objects
                    #     > 2 * self._max_observed_rate / self.__num_workers
                    # ):
                    #     self._recommended_num_objects = math.floor(
                    #         2 * self._max_observed_rate / self.__num_workers
                    #     )

                    refresh_time: float = 0.1
                except (RequestsHTTPError, ReadTimeout):
                    refresh_time = 0.1
                except Exception as e:
                    _Warnings.batch_refresh_failed(repr(e))
                    refresh_time = 10

                if self._active_threads < self.__num_workers:
                    self._active_thread_lock.acquire()
                    self._active_threads += 1
                    self._active_thread_lock.release()

                    send_thread = threading.Thread(
                        target=self.__send_batch_in_bg,
                        daemon=False,
                        name="SendBatch",
                        args=(
                            self.__batch_objects.pop_items(self._recommended_num_objects),
                            self.__batch_references.pop_items(self._recommended_num_refs),
                        ),
                    )
                    send_thread.start()
                time.sleep(refresh_time)

        demon = threading.Thread(
            target=periodic_check,
            daemon=True,
            name="batchSizeRefresh",
        )
        demon.start()


class _Batch2:
    def __init__(self, connection: Connection) -> None:
        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = None

        self.__current_batch: Optional[_Batch2Object] = None

    def __enter__(self) -> _Batch2Object:
        self.__current_batch = _Batch2Object(self.__connection, self.__consistency_level)
        return self.__current_batch

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self.__current_batch is not None
        self.__current_batch.flush()
        self.__current_batch = None

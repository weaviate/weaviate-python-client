import math
import time
from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from threading import Event, Thread
from typing import Any, Deque, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar

from pydantic import ValidationError

from requests import ReadTimeout
from requests.exceptions import HTTPError as RequestsHTTPError

from weaviate.cluster import Cluster
from weaviate.collection.classes.batch import (
    BatchObject,
    BatchReference,
    ErrorObject,
    ErrorReference,
    _BatchObject,
    BatchObjectReturn,
    _BatchReference,
    BatchReferenceReturn,
)
from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.grpc_batch import _BatchGRPC
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateBatchValidationError
from weaviate.warnings import _Warnings
from weaviate.weaviate_types import UUID, WeaviateField


class BatchExecutor(ThreadPoolExecutor):
    """
    Weaviate Batch Executor to run batch requests in separate thread.
    This class implements an additional method `is_shutdown` that is used by the context manager.
    """

    def is_shutdown(self) -> bool:
        return self._shutdown


BatchResponse = List[Dict[str, Any]]


TBatchInput = TypeVar("TBatchInput")
TBatchReturn = TypeVar("TBatchReturn")


class BatchRequest(ABC, Generic[TBatchInput, TBatchReturn]):
    """
    `BatchRequest` abstract class used as a interface for batch requests.
    """

    def __init__(self) -> None:
        self.__items: Deque[TBatchInput] = deque([])

    def __len__(self) -> int:
        return len(self.__items)

    def is_empty(self) -> bool:
        """
        Check if `BatchRequest` is empty.

        Returns
            `bool` Whether the `BatchRequest` is empty.
        """

        return len(self.__items) == 0

    def clear(self) -> None:
        """
        Remove all the items from the BatchRequest.
        """

        self.__items.clear()

    def add(self, item: TBatchInput) -> None:
        self.__items.append(item)

    @property
    def items(self) -> Deque[TBatchInput]:
        """
        Get all items from the BatchRequest.

        Returns
            `Deque[TBatchInput]` All items from the BatchRequest.
        """

        return self.__items

    @abstractmethod
    def _add_failed_objects_from_response(
        self,
        response_item: TBatchReturn,
        errors_to_exclude: Optional[List[str]] = None,
        errors_to_include: Optional[List[str]] = None,
    ) -> None:
        """Add failed items from a weaviate response.

        Parameters
        ----------
        response_item : BatchResponse
            Weaviate response that contains the status for all objects.
        errors_to_exclude : Optional[List[str]]
            Which errors should NOT be retried.
        errors_to_include : Optional[List[str]]
            Which errors should be retried.

        Returns
        ------
        BatchResponse: Contains responses form all successful object, eg. those that have not been added to this batch.
        """

    @staticmethod
    def _skip_objects_retry(
        entry: Dict[str, Any],
        errors_to_exclude: Optional[List[str]],
        errors_to_include: Optional[List[str]],
    ) -> bool:
        if (
            len(entry["result"]) == 0
            or "errors" not in entry["result"]
            or "error" not in entry["result"]["errors"]
            or len(entry["result"]["errors"]["error"]) == 0
        ):
            return True

        # skip based on error messages
        if errors_to_exclude is not None:
            for err in entry["result"]["errors"]["error"]:
                if any(excl in err["message"] for excl in errors_to_exclude):
                    return True
            return False
        elif errors_to_include is not None:
            for err in entry["result"]["errors"]["error"]:
                if any(incl in err["message"] for incl in errors_to_include):
                    return False
            return True
        return False


class ReferencesBatchRequest(BatchRequest[_BatchReference, BatchReferenceReturn]):
    """
    Collect Weaviate-object references to add them in one request to Weaviate.
    Caution this request will miss some validations to be faster.
    """

    def _add_failed_objects_from_response(
        self,
        return_: BatchReferenceReturn,
        errors_to_exclude: Optional[List[str]] = None,
        errors_to_include: Optional[List[str]] = None,
    ) -> None:
        # successful_responses = []

        for err in return_.errors.values():
            # if self._skip_objects_retry(ref, errors_to_exclude, errors_to_include):
            #     successful_responses.append(ref)
            #     continue
            self.add(err.reference)
        # return successful_responses


class ObjectsBatchRequest(BatchRequest[_BatchObject, BatchObjectReturn]):
    """
    Collect objects for one batch request to weaviate.
    Caution this batch will not be validated through weaviate.
    """

    def _add_failed_objects_from_response(
        self,
        return_: BatchObjectReturn,
        errors_to_exclude: Optional[List[str]] = None,
        errors_to_include: Optional[List[str]] = None,
    ) -> None:
        # successful_responses = []
        if return_.has_errors:
            for err in return_.errors.values():
                # if self._skip_objects_retry(obj, errors_to_exclude, errors_to_include):
                #     successful_responses.append(obj)
                #     continue
                self.add(err.object_)
        # return successful_responses


class _Batch:
    def __init__(
        self,
        connection: Connection,
        objects_: Optional[ObjectsBatchRequest] = None,
        references: Optional[ReferencesBatchRequest] = None,
    ) -> None:
        self.__batch_objects = objects_ or ObjectsBatchRequest()
        self.__batch_references = references or ReferencesBatchRequest()
        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = None
        self.__creation_time = min(self.__connection.timeout_config[1] / 10, 2)
        self.__batch = _BatchGRPC(connection, self.__consistency_level)
        self.__executor: Optional[BatchExecutor] = None
        self.__failed_objects: List[_BatchObject] = []
        self.__failed_references: List[_BatchReference] = []
        self.__future_pool_objects: Deque[Future[Tuple[BatchObjectReturn, int, bool]]] = deque([])
        self.__future_pool_references: Deque[
            Future[Tuple[BatchReferenceReturn, int, bool]]
        ] = deque([])
        self.__dynamic_batching = True
        self.__num_workers: int = 1
        self.__objects_throughput_frame: Deque[float] = deque(maxlen=5)
        self.__recommended_num_objects = 50
        self.__recommended_num_references = 50
        self.__reference_batch_queue: Deque[List[_BatchReference]] = deque([])
        self.__references_throughput_frame: Deque[float] = deque(maxlen=5)
        self.__retry_failed_objects: bool = False
        self.__retry_failed_references: bool = False
        self.__shut_background_thread_down: Optional[Event] = None

    def configure(
        self,
        dynamic: bool = True,
        consistency_level: Optional[ConsistencyLevel] = None,
        num_workers: Optional[int] = None,
        retry_failed_objects: bool = False,
        retry_failed_references: bool = False,
    ) -> None:
        """
        Configure your batch object.

        Every time you run this command, the `client.collection.batch` object will
        be updated with the new configuration. To enter the batching context manager, which handles automatically
        sending batches dynamically, use `with client.collection.batch as batch`.

        Arguments:
            `batch_size`
                The number of objects and references to be sent in one batch. If not provided, the default value is 50.
            `consistency_level`
                The consistency level to be used to send the batch. If not provided, the default value is None.
            `num_workers`
                The number of workers to be used to send the batch. If not provided, the default value is 1.
        """
        self.__consistency_level = consistency_level or self.__consistency_level
        self.__dynamic_batching = dynamic
        self.__num_workers = num_workers or self.__num_workers
        self.__retry_failed_objects = retry_failed_objects
        self.__retry_failed_references = retry_failed_references

    def num_objects(self) -> int:
        """
        Get current number of objects in the batch.

        Returns:
            `int`
                The number of objects in the batch.
        """

        return len(self.__batch_objects)

    def num_references(self) -> int:
        """
        Get current number of references in the batch.

        Returns:
            `int`
                The number of references in the batch.
        """

        return len(self.__batch_references)

    def failed_objects(self) -> List[_BatchObject]:
        """
        Get all failed objects from the batch manager.

        Returns:
            `List[_BatchObject]`
                A list of all the failed objects from the batch.
        """

        return self.__failed_objects

    def failed_references(self) -> List[_BatchReference]:
        """
        Get all failed references from the batch manager.

        Returns:
            `List[_BatchReference]`
                A list of all the failed references from the batch.
        """

        return self.__failed_references

    def start(self) -> "_Batch":
        """
        Start the BatchExecutor if it was closed.

        Returns:
            `Batch`
                The batch object with an open BatchExecutor and background running thread.
        """

        if self.__executor is None or self.__executor.is_shutdown():
            self.__executor = BatchExecutor(max_workers=self.__num_workers)

        if (
            self.__shut_background_thread_down is None
            or self.__shut_background_thread_down.is_set()
        ):
            self.__update_recommended_batch_size()

        return self

    def shutdown(self) -> None:
        """
        Shutdown the BatchExecutor.
        """
        if not (self.__executor is None or self.__executor.is_shutdown()):
            self.__executor.shutdown()

        if self.__shut_background_thread_down is not None:
            self.__shut_background_thread_down.set()

    def flush(self) -> None:
        """
        Flush both objects and references to the Weaviate server and call the callback function
        if one is provided. (See the docs for `configure` or `__call__` for how to set one.)

        This function is called when the context manager exits.
        """
        self.__send_batch_requests(force_wait=True)

    def __enter__(self) -> "_Batch":
        if not self.__dynamic_batching:
            raise WeaviateBatchValidationError(
                "Cannot use the batch context manager without dynamic batching. If you are doing manual batching, you must create them manually outside of the context manager with create_objects()"
            )
        self.__reset()
        return self.start()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.flush()
        self.shutdown()

    def __reset(self) -> None:
        self.__batch_objects.clear()
        self.__batch_references.clear()
        self.__future_pool_objects.clear()
        self.__future_pool_references.clear()
        self.__failed_objects.clear()
        self.__failed_references.clear()
        self.__reference_batch_queue.clear()

    def add_object(
        self,
        class_name: str,
        properties: Dict[str, WeaviateField],
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
        tenant: Optional[str] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Arguments:
            `properties`
                The data properties of the object to be added as a dictionary.
            `class_name`
                The name of the class this object belongs to.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            `vector`:
                The embedding of the object that should be validated. Can be used when a class does not have a vectorization module or the given vector was generated using the _identical_ vectorization module that is configured for the class. In this case this vector takes precedence. Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        try:
            batch_object = BatchObject(
                class_name=class_name,
                properties=properties,
                uuid=uuid,
                vector=vector,
                tenant=tenant,
            )
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__batch_objects.add(batch_object._to_internal())
        self.__auto_create()
        assert batch_object.uuid is not None
        return batch_object.uuid

    def add_reference(
        self,
        from_object_uuid: UUID,
        from_object_class_name: str,
        from_property_name: str,
        to_object_uuid: UUID,
        to_object_class_name: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """
        Add one reference to this batch.

        Arguments:
            `from_object_uuid`
                The UUID of the object, as an uuid.UUID object or str, that should reference another object.
                It can be a Weaviate beacon or Weaviate href.
            `from_object_class_name`
                The name of the class that should reference another object.
            `from_property_name`
                The name of the property that contains the reference.
            `to_object_uuid`
                The UUID of the object, as an uuid.UUID object or str, that is actually referenced.
                It can be a Weaviate beacon or Weaviate href.
            `to_object_class_name`
                The referenced object class name to which to add the reference (with UUID `to_object_uuid`).
            `tenant`
                Name of the tenant.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        try:
            batch_reference = BatchReference(
                from_object_class_name=from_object_class_name,
                from_object_uuid=from_object_uuid,
                from_property_name=from_property_name,
                to_object_class_name=to_object_class_name,
                to_object_uuid=to_object_uuid,
                tenant=tenant,
            )
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__batch_references.add(batch_reference._to_internal())
        self.__auto_create()

    def create_objects(self) -> BatchObjectReturn:
        """
        Send all the currently batched objects to Weaviate manually.

        This function will do nothing unless you set `dynamic` to `False` in `configure`.
        """
        if self.__dynamic_batching:
            _Warnings.batch_create_dynamic("objects")
            return BatchObjectReturn(
                all_responses=[],
                uuids={},
                errors={},
                elapsed_seconds=0,
                has_errors=False,
            )
        res = self.__flush_objects(list(self.__batch_objects.items))
        self.__batch_objects.clear()
        return res[0]

    def create_references(self) -> BatchReferenceReturn:
        """
        Send all the currently batched references to Weaviate manually.

        This function will do nothing unless you set `dynamic` to `False` in `configure`.
        """
        if self.__dynamic_batching:
            _Warnings.batch_create_dynamic("references")
            return BatchReferenceReturn(
                elapsed_seconds=0,
                errors={},
                has_errors=False,
            )
        res = self.__flush_references(list(self.__batch_references.items))
        self.__batch_references.clear()
        return res[0]

    def __auto_create(self) -> None:
        if (
            self.num_objects() >= self.__recommended_num_objects
            or self.num_references() >= self.__recommended_num_references
        ):
            while self.__recommended_num_objects == 0 or self.__recommended_num_references == 0:
                sleep = 1
                _Warnings.batch_weaviate_overloaded_sleeping(sleep)
                time.sleep(sleep)  # block if weaviate is overloaded
            self.__send_batch_requests(force_wait=False)

    def __flush_objects(self, batch: List[_BatchObject]) -> Tuple[BatchObjectReturn, int, bool]:
        start = time.time()
        try:
            return_ = self.__batch.objects(
                objects=batch,
            )
            return return_, len(batch), False
        except Exception as e:
            print(repr(e), batch)
            errors = {
                idx: ErrorObject(message=repr(e), object_=obj) for idx, obj in enumerate(batch)
            }
            return (
                BatchObjectReturn(
                    all_responses=list(errors.values()),
                    elapsed_seconds=time.time() - start,
                    errors=errors,
                    has_errors=True,
                    uuids={},
                ),
                0,
                True,
            )

    def __flush_references(
        self, batch: List[_BatchReference]
    ) -> Tuple[BatchReferenceReturn, int, bool]:
        start = time.time()
        try:
            response = self.__batch.references(
                references=batch,
            )
            return response, len(batch), False
        except Exception as e:
            print(repr(e), batch)
            errors = {
                idx: ErrorReference(message=repr(e), reference=ref) for idx, ref in enumerate(batch)
            }
            return (
                BatchReferenceReturn(
                    elapsed_seconds=time.time() - start,
                    errors=errors,
                    has_errors=True,
                ),
                0,
                True,
            )

    def __send_batch_requests(self, force_wait: bool, how_many_recursions: int = 0) -> None:
        if self.__executor is None:
            self.start()
        elif self.__executor.is_shutdown():
            _Warnings.batch_executor_is_shutdown()
            self.start()

        assert self.__executor is not None

        if len(self.__batch_objects) > 0:
            self.__future_pool_objects.append(
                self.__executor.submit(
                    self.__flush_objects,
                    batch=list(self.__batch_objects.items),
                )
            )
        if len(self.__batch_references) > 0:
            # convert deque to list to ensure data is copied before being clearer below
            self.__reference_batch_queue.append(list(self.__batch_references.items))

        self.__batch_objects.clear()
        self.__batch_references.clear()

        if (
            not force_wait
            and self.__num_workers > 1
            and len(self.__future_pool_objects) < self.__num_workers
        ):
            return

        for done_obj_future in as_completed(self.__future_pool_objects):
            ret_objs, nr_objs, exception_raised = done_obj_future.result()
            if self.__retry_failed_objects and (exception_raised or ret_objs.has_errors):
                self.__batch_objects._add_failed_objects_from_response(ret_objs)
                self.__backoff_recommended_object_batch_size(True)
            else:
                self.__objects_throughput_frame.append(nr_objs / ret_objs.elapsed_seconds)
                self.__failed_objects.extend([err.object_ for err in ret_objs.errors.values()])

        for ref_batch_items in self.__reference_batch_queue:
            self.__future_pool_references.append(
                self.__executor.submit(
                    self.__flush_references,
                    batch=list(ref_batch_items),
                )
            )

        for done_ref_future in as_completed(self.__future_pool_references):
            ret_refs, nr_refs, exception_raised = done_ref_future.result()
            if self.__retry_failed_references and (exception_raised or ret_refs.has_errors):
                self.__batch_references._add_failed_objects_from_response(ret_refs)
                self.__backoff_recommended_reference_batch_size(True)
            else:
                self.__references_throughput_frame.append(nr_refs / ret_refs.elapsed_seconds)
                self.__failed_references.extend([err.reference for err in ret_refs.errors.values()])

        # Clear futures before checking if we need to retry
        self.__future_pool_objects.clear()
        self.__future_pool_references.clear()
        self.__reference_batch_queue.clear()

        if len(self.__batch_objects) > 0 or len(self.__batch_references) > 0:
            if how_many_recursions == 4:
                _Warnings.batch_retrying_failed_batches_hit_hard_limit(5)
                self.__failed_objects = list(self.__batch_objects.items)
                self.__failed_references = list(self.__batch_references.items)
            else:
                self.__send_batch_requests(
                    force_wait=True, how_many_recursions=how_many_recursions + 1
                )

    def __backoff_recommended_object_batch_size(self, exception_occurred: bool) -> None:
        if exception_occurred and self.__recommended_num_objects is not None:
            self.__recommended_num_objects = max(self.__recommended_num_objects // 2, 1)
        elif (
            len(self.__objects_throughput_frame) != 0
            and self.__recommended_num_objects is not None
            and not self.__dynamic_batching
        ):
            obj_per_second = (
                sum(self.__objects_throughput_frame) / len(self.__objects_throughput_frame) * 0.75
            )
            self.__recommended_num_objects = max(
                min(
                    round(obj_per_second * self.__creation_time),
                    self.__recommended_num_objects + 250,
                ),
                1,
            )

    def __backoff_recommended_reference_batch_size(self, exception_occurred: bool) -> None:
        if exception_occurred and self.__recommended_num_references is not None:
            self.__recommended_num_references = max(self.__recommended_num_references // 2, 1)
        elif (
            len(self.__references_throughput_frame) != 0
            and self.__recommended_num_references is not None
        ):
            ref_per_sec = sum(self.__references_throughput_frame) / len(
                self.__references_throughput_frame
            )
            self.__recommended_num_references = min(
                round(ref_per_sec * self.__creation_time),
                self.__recommended_num_references * 2,
            )

    def __update_recommended_batch_size(self) -> None:
        """Create a background process that periodically checks how congested the batch queue is."""
        self.__shut_background_thread_down = Event()

        def periodic_check() -> None:
            cluster = Cluster(self.__connection)
            while (
                self.__shut_background_thread_down is not None
                and not self.__shut_background_thread_down.is_set()
            ):
                try:
                    status = cluster.get_nodes_status()
                    if "stats" not in status[0] or "ratePerSecond" not in status[0]["stats"]:
                        self.__dynamic_batching = False
                        return
                    rate = status[0]["batchStats"]["ratePerSecond"]
                    rate_per_worker = rate / self.__num_workers
                    batch_length = status[0]["batchStats"]["queueLength"]

                    if batch_length == 0:  # scale up if queue is empty
                        self.__recommended_num_objects = self.__recommended_num_objects + min(
                            self.__recommended_num_objects * 2, 25
                        )
                    else:
                        ratio = batch_length / rate
                        if (
                            2.1 > ratio > 1.9
                        ):  # ideal, send exactly as many objects as weaviate can process
                            self.__recommended_num_objects = math.floor(rate_per_worker)
                        elif ratio <= 1.9:  # we can send more
                            self.__recommended_num_objects = math.floor(
                                min(
                                    self.__recommended_num_objects * 1.5,
                                    rate_per_worker * 2 / ratio,
                                )
                            )
                        elif ratio < 10:  # too high, scale down
                            self.__recommended_num_objects = math.floor(rate_per_worker * 2 / ratio)
                        else:  # way too high, stop sending new batches
                            self.__recommended_num_objects = 0

                    refresh_time: float = 2
                except (RequestsHTTPError, ReadTimeout):
                    refresh_time = 0.1
                except Exception as e:
                    _Warnings.batch_refresh_failed(repr(e))
                    refresh_time = 10

                time.sleep(refresh_time)
            self.__recommended_num_objects = 10  # in case some batch needs to be send afterwards
            self.__shut_background_thread_down = None

        demon = Thread(
            target=periodic_check,
            daemon=True,
            name="batchSizeRefresh",
        )
        demon.start()

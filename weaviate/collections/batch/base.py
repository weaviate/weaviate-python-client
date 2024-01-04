import asyncio
import math
import threading
import time
from abc import ABC, abstractmethod
from copy import copy
from typing import Any, Dict, Generic, List, Optional, Sequence, Set, TypeVar

from pydantic import ValidationError
from requests import ReadTimeout
from requests.exceptions import HTTPError as RequestsHTTPError

from weaviate.cluster import Cluster
from weaviate.collections.batch.grpc import _BatchGRPC
from weaviate.collections.batch.rest import _BatchRESTAsync
from weaviate.collections.classes.batch import (
    BatchObject,
    BatchReference,
    BatchResult,
    ErrorObject,
    ErrorReference,
    _BatchObject,
    BatchObjectReturn,
    _BatchReference,
    BatchReferenceReturn,
    Shard,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import WeaviateReferences
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateBatchValidationError
from weaviate.types import UUID
from weaviate.warnings import _Warnings

BatchResponse = List[Dict[str, Any]]


TBatchInput = TypeVar("TBatchInput")
TBatchReturn = TypeVar("TBatchReturn")


class BatchRequest(ABC, Generic[TBatchInput, TBatchReturn]):
    """`BatchRequest` abstract class used as a interface for batch requests."""

    def __init__(self) -> None:
        self.__items: List[TBatchInput] = []
        self.__lock = threading.Lock()

    def __len__(self) -> int:
        return len(self.__items)

    def clear(self) -> None:
        """Remove all the items from the BatchRequest."""
        self.__items.clear()

    def add(self, item: TBatchInput) -> None:
        """Add an item to the BatchRequest."""
        self.__lock.acquire()
        self.__items.append(item)
        self.__lock.release()

    @property
    def items(self) -> List[TBatchInput]:
        """
        Get all items from the BatchRequest.

        Returns
            `Deque[TBatchInput]` All items from the BatchRequest.
        """
        return self.__items

    def pop_items(self, pop_amount: int) -> List[TBatchInput]:
        """Pop the given number of items from the BatchRequest queue.

        Returns
            `List[TBatchInput]` items from the BatchRequest.
        """
        self.__lock.acquire()
        if pop_amount >= len(self.__items):
            ret = copy(self.__items)
            self.__items.clear()
        else:
            ret = copy(self.__items[:pop_amount])
            self.__items = self.__items[pop_amount:]

        self.__lock.release()
        return ret

    @abstractmethod
    def _add_failed_objects_from_response(
        self,
        response_item: TBatchReturn,
        errors_to_exclude: Optional[List[str]] = None,
        errors_to_include: Optional[List[str]] = None,
    ) -> None:
        """Add failed items from a weaviate response.

        Arguments:
            `response_item`
                Weaviate response that contains the status for all objects.
            `errors_to_exclude`
                Which errors should NOT be retried.
            `errors_to_include`
                Which errors should be retried.

        Returns:
            `BatchResponse`
                Contains responses form all successful object, eg. those that have not been added to this batch.
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


B = TypeVar("B", bound="_BatchBase")


class _BatchBase:
    def __init__(
        self,
        connection: Connection,
        consistency_level: Optional[ConsistencyLevel] = None,
        fixed_batch_size: Optional[int] = None,  # dynamic by default
        fixed_concurrent_requests: Optional[int] = None,  # dynamic by default
        objects_: Optional[ObjectsBatchRequest] = None,
        references: Optional[ReferencesBatchRequest] = None,
    ) -> None:
        self.__batch_objects = objects_ or ObjectsBatchRequest()
        self.__batch_references = references or ReferencesBatchRequest()
        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = consistency_level

        self.__batch_grpc = _BatchGRPC(connection, self.__consistency_level)
        self.__batch_rest = _BatchRESTAsync(connection, self.__consistency_level)

        self.__result: BatchResult = BatchResult()
        self._failed_objects: List[ErrorObject] = []
        self._failed_references: List[ErrorReference] = []
        self.__results_lock = threading.Lock()

        self.__retry_failed_objects: bool = False
        self.__retry_failed_references: bool = False
        self._imported_shards: Set[Shard] = set()

        self.__cluster = Cluster(self.__connection)

        self._max_batch_size: int = 1000
        self.__dynamic_batching = fixed_batch_size is None
        self._recommended_num_objects: int = (
            fixed_batch_size if fixed_batch_size is not None else 10
        )
        # there seems to be a bug with weaviate when sending > 50 refs at once
        self._recommended_num_refs: int = 50

        self.__num_workers: int = (
            fixed_concurrent_requests if fixed_concurrent_requests is not None else 2
        )
        self._active_threads = 0
        self._active_thread_lock = threading.Lock()
        self._last_scale_up: float = 0
        self._max_observed_rate: int = 0

        self._loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        self.__start_bg_thread()

    def __start_bg_thread(self) -> None:
        """Create a background process that periodically checks how congested the batch queue is."""
        self.__shut_background_thread_down = threading.Event()

        def start_event_loop_thread() -> None:
            while (
                self.__shut_background_thread_down is not None
                and not self.__shut_background_thread_down.is_set()
            ):
                if self._loop.is_running():
                    continue
                else:
                    self._loop.run_forever()

        event_loop = threading.Thread(
            target=start_event_loop_thread,
            daemon=True,
            name="eventLoop",
        )
        event_loop.start()

        def periodic_check() -> None:
            while (
                self.__shut_background_thread_down is not None
                and not self.__shut_background_thread_down.is_set()
            ):
                if not self.__dynamic_batching:
                    refresh_time: float = 0.1
                else:
                    try:
                        status = self.__cluster.get_nodes_status()
                        if (
                            "batchStats" not in status[0]
                            or "queueLength" not in status[0]["batchStats"]
                        ):
                            # async indexing - just send a lot
                            self.__dynamic_batching = False
                            self._recommended_num_objects = 1000
                            self.__num_workers = 10
                            continue

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
                                self._recommended_num_objects = math.floor(
                                    rate_per_worker * 2 / ratio
                                )

                                if self._recommended_num_objects < 100 and self.__num_workers > 2:
                                    self.__num_workers -= 1

                            else:  # way too high, stop sending new batches
                                self._recommended_num_objects = 0
                                self.__num_workers = 2

                        refresh_time = 0.01
                    except (RequestsHTTPError, ReadTimeout):
                        refresh_time = 0.1
                    except Exception as e:
                        _Warnings.batch_refresh_failed(repr(e))
                        refresh_time = 10

                if self._active_threads < self.__num_workers and (
                    len(self.__batch_objects) > 0 or len(self.__batch_references) > 0
                ):
                    self._active_thread_lock.acquire()
                    self._active_threads += 1
                    self._active_thread_lock.release()
                    asyncio.run_coroutine_threadsafe(
                        self.__send_batch_async(
                            self.__batch_objects.pop_items(self._recommended_num_objects),
                            self.__batch_references.pop_items(self._recommended_num_refs),
                        ),
                        self._loop,
                    )

                time.sleep(refresh_time)

        demon = threading.Thread(
            target=periodic_check,
            daemon=True,
            name="batchSizeRefresh",
        )
        demon.start()

    async def __send_batch_async(
        self, objs: List[_BatchObject], refs: List[_BatchReference]
    ) -> None:
        if len(objs) > 0:
            start = time.time()
            try:
                response_obj = await self.__batch_grpc.objects_async(objects=objs)
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
            self._failed_objects.extend(response_obj.errors.values())
            self.__results_lock.release()

            if self.__retry_failed_objects and response_obj.has_errors:
                self.__batch_objects._add_failed_objects_from_response(response_obj)

        if len(refs) > 0:
            start = time.time()
            try:
                response_ref = await self.__batch_rest.references(references=refs)

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
            if self.__retry_failed_references and response_ref.has_errors:
                self.__batch_references._add_failed_objects_from_response(response_ref)
            self.__results_lock.acquire()
            self.__result.refs += response_ref
            self._failed_references.extend(response_ref.errors.values())
            self.__results_lock.release()

        self._active_thread_lock.acquire()
        self._active_threads -= 1
        self._active_thread_lock.release()

    def failed_objects(self) -> List[ErrorObject]:
        return self._failed_objects

    def failed_references(self) -> List[ErrorReference]:
        return self._failed_references

    def results(self) -> BatchResult:
        return self.__result

    def flush(self) -> None:
        # bg thread is sending objs+refs automatically, so simply wait for everything to be done
        while (
            self._active_threads > 0
            or len(self.__batch_objects) > 0
            or len(self.__batch_references) > 0
        ):
            time.sleep(0.01)

        # we are done, shut bg thread down
        self.__shut_background_thread_down.set()
        self._loop.stop()

    def _add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[WeaviateReferences] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
        tenant: Optional[str] = None,
    ) -> UUID:
        try:
            batch_object = BatchObject(
                collection=collection,
                properties=properties,
                references=references,
                uuid=uuid,
                vector=vector,
                tenant=tenant,
            )
            self._imported_shards.add(Shard(collection=collection, tenant=tenant))
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__batch_objects.add(batch_object._to_internal())

        # block if queue gets too long or weaviate is overloaded - reading files is faster them sending them so we do
        # not need a long queue
        while (
            self._recommended_num_objects == 0
            or len(self.__batch_objects) >= self._recommended_num_objects * 10
        ):
            time.sleep(1)

        assert batch_object.uuid is not None
        return batch_object.uuid

    def _add_reference(
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
        while self._recommended_num_objects == 0:
            time.sleep(1)  # block if weaviate is overloaded, also do not send any refs

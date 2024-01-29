import asyncio
import math
import threading
import time
import uuid as uuid_package
from abc import ABC
from copy import copy
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Set,
    TypeVar,
    Union,
)

from pydantic import ValidationError
from requests import ReadTimeout
from requests.exceptions import HTTPError as RequestsHTTPError
from typing_extensions import TypeAlias

from weaviate.cluster import Cluster
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
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
from weaviate.collections.classes.internal import (
    ReferenceToMulti,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateBatchValidationError
from weaviate.types import UUID
from weaviate.warnings import _Warnings

BatchResponse = List[Dict[str, Any]]


TBatchInput = TypeVar("TBatchInput")
TBatchReturn = TypeVar("TBatchReturn")
MAX_CONCURRENT_REQUESTS = 10
DEFAULT_REQUEST_TIMEOUT = 120


class BatchRequest(ABC, Generic[TBatchInput, TBatchReturn]):
    """`BatchRequest` abstract class used as a interface for batch requests."""

    def __init__(self) -> None:
        self.__items: List[TBatchInput] = []
        self.__lock = threading.Lock()

    def __len__(self) -> int:
        return len(self.__items)

    def add(self, item: TBatchInput) -> None:
        """Add an item to the BatchRequest."""
        self.__lock.acquire()
        self.__items.append(item)
        self.__lock.release()

    def prepend(self, item: List[TBatchInput]) -> None:
        """Add items to the front of the BatchRequest.

        This is intended to be used when objects should be retries, eg. after a temporary error.
        """
        self.__lock.acquire()
        self.__items = item + self.__items
        self.__lock.release()

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


class ReferencesBatchRequest(BatchRequest[_BatchReference, BatchReferenceReturn]):
    """Collect Weaviate-object references to add them in one request to Weaviate."""


class ObjectsBatchRequest(BatchRequest[_BatchObject, BatchObjectReturn]):
    """Collect objects for one batch request to weaviate."""


@dataclass
class _BatchDataWrapper:
    results: BatchResult = field(default_factory=BatchResult)
    failed_objects: List[ErrorObject] = field(default_factory=list)
    failed_references: List[ErrorReference] = field(default_factory=list)
    imported_shards: Set[Shard] = field(default_factory=set)


@dataclass
class _DynamicBatching:
    pass


@dataclass
class _FixedSizeBatching:
    batch_size: int
    concurrent_requests: int


@dataclass
class _RateLimitedBatching:
    requests_per_minute: int


_BatchMode: TypeAlias = Union[_DynamicBatching, _FixedSizeBatching, _RateLimitedBatching]


class _BatchBase:
    def __init__(
        self,
        connection: ConnectionV4,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        batch_mode: _BatchMode,
        objects_: Optional[ObjectsBatchRequest] = None,
        references: Optional[BatchRequest[_BatchReference, BatchReferenceReturn]] = None,
    ) -> None:
        self.__batch_objects = objects_ or ObjectsBatchRequest()
        self.__batch_references = (
            references or BatchRequest[_BatchReference, BatchReferenceReturn]()
        )
        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = consistency_level

        self.__batch_grpc = _BatchGRPC(connection, self.__consistency_level)
        self.__batch_rest = _BatchRESTAsync(connection, self.__consistency_level)

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__results_lock = threading.Lock()

        self.__cluster = Cluster(self.__connection)

        self.__batching_mode: _BatchMode = batch_mode
        self.__max_batch_size: int = 1000

        if isinstance(self.__batching_mode, _FixedSizeBatching):
            self.__recommended_num_objects = self.__batching_mode.batch_size
            self.__concurrent_requests = self.__batching_mode.concurrent_requests
        elif isinstance(self.__batching_mode, _RateLimitedBatching):
            # Batch with rate limiting should never send more than the given amount of objects per minute.
            # We could send all objects in a single batch every 60 seconds but that could cause problems with too large requests. Therefore, we
            # limit the size of a batch to self.__max_batch_size and send multiple batches of equal size and send them in equally space in time.
            # Example:
            #  3000 objects, 1000/min -> 3 batches of 1000 objects, send every 20 seconds
            self.__concurrent_requests = (
                self.__batching_mode.requests_per_minute + self.__max_batch_size
            ) // self.__max_batch_size
            self.__recommended_num_objects = (
                self.__batching_mode.requests_per_minute // self.__concurrent_requests
            )
        else:
            assert isinstance(self.__batching_mode, _DynamicBatching)
            self.__recommended_num_objects = 10
            self.__concurrent_requests = 2

        # there seems to be a bug with weaviate when sending > 50 refs at once
        self.__recommended_num_refs: int = 50

        self.__active_requests = 0
        self.__active_requests_lock = threading.Lock()

        # dynamic batching
        self.__time_last_scale_up: float = 0
        self.__max_observed_rate: int = 0

        # fixed rate batching
        self.__time_stamp_last_request: float = 0
        # do 62 secs to give us some buffer to the "per-minute" calculation
        self.__fix_rate_batching_base_time = 62 // self.__concurrent_requests

        self.__bg_thread = self.__start_bg_thread()
        self.__bg_thread_exception: Optional[Exception] = None

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

    def __run_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        try:
            loop.run_forever()
        finally:
            # This is entered when loop.stop is scheduled from the main thread
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def __start_new_event_loop(self) -> asyncio.AbstractEventLoop:
        loop = asyncio.new_event_loop()

        event_loop = threading.Thread(
            target=self.__run_event_loop,
            daemon=True,
            args=(loop,),
            name="eventLoop",
        )
        event_loop.start()

        while not loop.is_running():
            time.sleep(0.01)

        return loop

    def _shutdown(self) -> None:
        """Shutdown the current batch and wait for all requests to be finished."""
        self.flush()

        # we are done, shut bg threads down and end the event loop
        self.__shut_background_thread_down.set()
        while self.__bg_thread.is_alive():
            time.sleep(0.01)

        # copy the results to the public results
        self.__results_for_wrapper_backup.results = self.__results_for_wrapper.results
        self.__results_for_wrapper_backup.failed_objects = self.__results_for_wrapper.failed_objects
        self.__results_for_wrapper_backup.failed_references = (
            self.__results_for_wrapper.failed_references
        )
        self.__results_for_wrapper_backup.imported_shards = (
            self.__results_for_wrapper.imported_shards
        )

    def __periodic_check(self) -> None:
        loop = self.__start_new_event_loop()
        future = asyncio.run_coroutine_threadsafe(self.__connection.aopen(), loop)
        future.result()  # Wait for self._connection.aopen() to finish

        while (
            self.__shut_background_thread_down is not None
            and not self.__shut_background_thread_down.is_set()
        ):
            if isinstance(self.__batching_mode, _FixedSizeBatching):
                refresh_time: float = 0.01
            elif isinstance(self.__batching_mode, _RateLimitedBatching):
                if (
                    time.time() - self.__time_stamp_last_request
                    < self.__fix_rate_batching_base_time // self.__concurrent_requests
                ):
                    time.sleep(1)
                    continue

                self.__time_stamp_last_request = time.time()
                refresh_time = 0
            else:
                assert isinstance(self.__batching_mode, _DynamicBatching)
                try:
                    self.__dynamic_batching()
                    refresh_time = 0.001
                except (RequestsHTTPError, ReadTimeout):
                    refresh_time = 0.1
                except Exception as e:
                    _Warnings.batch_refresh_failed(repr(e))
                    refresh_time = 10

            if self.__active_requests < self.__concurrent_requests and (
                len(self.__batch_objects) > 0 or len(self.__batch_references) > 0
            ):
                self.__active_requests_lock.acquire()
                self.__active_requests += 1
                self.__active_requests_lock.release()

                # do not block the thread - the results are written to a central (locked) list and we want to have multiple concurrent batch-requests
                asyncio.run_coroutine_threadsafe(
                    self.__send_batch_async(
                        self.__batch_objects.pop_items(self.__recommended_num_objects),
                        self.__batch_references.pop_items(self.__recommended_num_refs),
                        readd_rate_limit=isinstance(self.__batching_mode, _RateLimitedBatching),
                    ),
                    loop,
                )

            time.sleep(refresh_time)

        future = asyncio.run_coroutine_threadsafe(self.__connection.aclose(), loop)
        future.result()  # Wait for self._connection.aclose() to finish
        loop.call_soon_threadsafe(loop.stop)

    def __start_bg_thread(self) -> threading.Thread:
        """Create a background thread that periodically checks how congested the batch queue is."""
        self.__shut_background_thread_down = threading.Event()

        def periodic_check_wrapper() -> None:
            try:
                self.__periodic_check()
            except Exception as e:
                self.__bg_thread_exception = e

        demon = threading.Thread(
            target=periodic_check_wrapper,
            daemon=True,
            name="BgBatchScheduler",
        )
        demon.start()
        return demon

    def __dynamic_batching(self) -> None:
        status = self.__cluster.get_nodes_status()
        if "batchStats" not in status[0] or "queueLength" not in status[0]["batchStats"]:
            # async indexing - just send a lot
            self.__batching_mode = _FixedSizeBatching(1000, 10)
            self.__recommended_num_objects = 1000
            self.__concurrent_requests = 10
            return

        rate = status[0]["batchStats"]["ratePerSecond"]
        rate_per_worker = rate / self.__concurrent_requests

        batch_length = status[0]["batchStats"]["queueLength"]

        if rate > self.__max_observed_rate:
            self.__max_observed_rate = rate

        if batch_length == 0:  # scale up if queue is empty
            self.__recommended_num_objects = min(
                self.__recommended_num_objects + 50,
                self.__max_batch_size,
            )

            if (
                self.__max_batch_size == self.__recommended_num_objects
                and len(self.__batch_objects) > self.__recommended_num_objects
                and time.time() - self.__time_last_scale_up > 1
                and self.__concurrent_requests < MAX_CONCURRENT_REQUESTS
            ):
                self.__concurrent_requests += 1
                self.__time_last_scale_up = time.time()

        else:
            ratio = batch_length / rate
            if 2.1 > ratio > 1.9:  # ideal, send exactly as many objects as weaviate can process
                self.__recommended_num_objects = math.floor(rate_per_worker)
            elif ratio <= 1.9:  # we can send more
                self.__recommended_num_objects = math.floor(
                    min(
                        self.__recommended_num_objects * 1.5,
                        rate_per_worker * 2 / ratio,
                    )
                )

                if self.__max_batch_size == self.__recommended_num_objects:
                    self.__concurrent_requests += 1

            elif ratio < 10:  # too high, scale down
                self.__recommended_num_objects = math.floor(rate_per_worker * 2 / ratio)

                if self.__recommended_num_objects < 100 and self.__concurrent_requests > 2:
                    self.__concurrent_requests -= 1

            else:  # way too high, stop sending new batches
                self.__recommended_num_objects = 0
                self.__concurrent_requests = 2

    async def __send_batch_async(
        self, objs: List[_BatchObject], refs: List[_BatchReference], readd_rate_limit: bool
    ) -> None:
        if len(objs) > 0:
            start = time.time()
            try:
                response_obj = await self.__batch_grpc.aobjects(
                    objects=objs, timeout=DEFAULT_REQUEST_TIMEOUT
                )
            except Exception as e:
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

            if readd_rate_limit:
                readded_objects = []
                highest_retry_count = 0
                for i, err in response_obj.errors.items():
                    if ("support@cohere.com" in err.message and "rate limit" in err.message) or (
                        "rate_limit_exceeded" in err.message
                    ):
                        if err.object_.retry_count > highest_retry_count:
                            highest_retry_count = err.object_.retry_count

                        if err.object_.retry_count > 5:
                            continue  # too many retries, give up
                        err.object_.retry_count += 1
                        readded_objects.append(i)

                if len(readded_objects) > 0:
                    _Warnings.batch_rate_limit_reached(
                        response_obj.errors[readded_objects[0]].message,
                        self.__fix_rate_batching_base_time * (highest_retry_count + 1),
                    )

                    self.__batch_objects.prepend(
                        [
                            err.object_
                            for i, err in response_obj.errors.items()
                            if i in readded_objects
                        ]
                    )

                    new_errors = {
                        i: err for i, err in response_obj.errors.items() if i not in readded_objects
                    }
                    response_obj = BatchObjectReturn(
                        uuids={
                            i: uid
                            for i, uid in response_obj.uuids.items()
                            if i not in readded_objects
                        },
                        errors=new_errors,
                        has_errors=len(new_errors) > 0,
                        all_responses=[
                            err
                            for i, err in enumerate(response_obj.all_responses)
                            if i not in readded_objects
                        ],
                        elapsed_seconds=response_obj.elapsed_seconds,
                    )
                    self.__time_stamp_last_request = (
                        time.time() + self.__fix_rate_batching_base_time * (highest_retry_count + 1)
                    )  # skip a full minute to recover from the rate limit
                    self.__fix_rate_batching_base_time += (
                        1  # increase the base time as the current one is too low
                    )

            self.__results_lock.acquire()
            self.__results_for_wrapper.results.objs += response_obj
            self.__results_for_wrapper.failed_objects.extend(response_obj.errors.values())
            self.__results_lock.release()

        if len(refs) > 0:
            start = time.time()
            try:
                response_ref = await self.__batch_rest.references(references=refs)

            except Exception as e:
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
            self.__results_for_wrapper.results.refs += response_ref
            self.__results_for_wrapper.failed_references.extend(response_ref.errors.values())
            self.__results_lock.release()

        self.__active_requests_lock.acquire()
        self.__active_requests -= 1
        self.__active_requests_lock.release()

    def flush(self) -> None:
        """Flush the batch queue and wait for all requests to be finished."""
        # bg thread is sending objs+refs automatically, so simply wait for everything to be done
        while (
            self.__active_requests > 0
            or len(self.__batch_objects) > 0
            or len(self.__batch_references) > 0
        ):
            time.sleep(0.01)
            self.__check_bg_thread_alive()

    def _add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
        tenant: Optional[str] = None,
    ) -> UUID:
        self.__check_bg_thread_alive()
        try:
            batch_object = BatchObject(
                collection=collection,
                properties=properties,
                references=references,
                uuid=uuid,
                vector=vector,
                tenant=tenant,
            )
            self.__results_for_wrapper.imported_shards.add(
                Shard(collection=collection, tenant=tenant)
            )
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__batch_objects.add(batch_object._to_internal())

        # block if queue gets too long or weaviate is overloaded - reading files is faster them sending them so we do
        # not need a long queue
        while (
            self.__recommended_num_objects == 0
            or len(self.__batch_objects) >= self.__recommended_num_objects * 10
        ):
            self.__check_bg_thread_alive()
            time.sleep(0.01)

        assert batch_object.uuid is not None
        return batch_object.uuid

    def _add_reference(
        self,
        from_object_uuid: UUID,
        from_object_collection: str,
        from_property_name: str,
        to: ReferenceInput,
        tenant: Optional[str] = None,
    ) -> None:
        self.__check_bg_thread_alive()
        if isinstance(to, ReferenceToMulti):
            to_strs: Union[List[str], List[UUID]] = to.uuids_str
        elif isinstance(to, str) or isinstance(to, uuid_package.UUID):
            to_strs = [to]
        else:
            to_strs = list(to)

        for uid in to_strs:
            try:
                batch_reference = BatchReference(
                    from_object_collection=from_object_collection,
                    from_object_uuid=from_object_uuid,
                    from_property_name=from_property_name,
                    to_object_collection=(
                        to.target_collection if isinstance(to, ReferenceToMulti) else None
                    ),
                    to_object_uuid=uid,
                    tenant=tenant,
                )
            except ValidationError as e:
                raise WeaviateBatchValidationError(repr(e))
            self.__batch_references.add(batch_reference._to_internal())

        # block if queue gets too long or weaviate is overloaded
        while self.__recommended_num_objects == 0:
            time.sleep(0.01)  # block if weaviate is overloaded, also do not send any refs
            self.__check_bg_thread_alive()

    def __check_bg_thread_alive(self) -> None:
        if self.__bg_thread.is_alive():
            return

        raise self.__bg_thread_exception or Exception("Batch thread died unexpectedly")

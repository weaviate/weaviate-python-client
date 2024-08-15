import math
import threading
import time
import uuid as uuid_package
from abc import ABC
from collections import deque
from copy import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Set, TypeVar, Union, cast

from pydantic import ValidationError
from typing_extensions import TypeAlias

from httpx import ConnectError

from weaviate.cluster.types import Node
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.batch.rest import _BatchREST
from weaviate.collections.classes.batch import (
    _BatchReference,
    BatchObject,
    BatchReference,
    BatchResult,
    ErrorObject,
    ErrorReference,
    _BatchObject,
    BatchObjectReturn,
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
from weaviate.event_loop import _EventLoop
from weaviate.exceptions import WeaviateBatchValidationError, EmptyResponseException
from weaviate.logger import logger
from weaviate.types import UUID, VECTORS
from weaviate.util import _decode_json_response_dict
from weaviate.warnings import _Warnings

BatchResponse = List[Dict[str, Any]]


TBatchInput = TypeVar("TBatchInput")
TBatchReturn = TypeVar("TBatchReturn")
MAX_CONCURRENT_REQUESTS = 10
DEFAULT_REQUEST_TIMEOUT = 180
CONCURRENT_REQUESTS_DYNAMIC_VECTORIZER = 2
BATCH_TIME_TARGET = 10
VECTORIZER_BATCHING_STEP_SIZE = 48  # cohere max batch size is 96


class BatchRequest(ABC, Generic[TBatchInput, TBatchReturn]):
    """`BatchRequest` abstract class used as a interface for batch requests."""

    def __init__(self) -> None:
        self._items: List[TBatchInput] = []
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._items)

    def add(self, item: TBatchInput) -> None:
        """Add an item to the BatchRequest."""
        self._lock.acquire()
        self._items.append(item)
        self._lock.release()

    def prepend(self, item: List[TBatchInput]) -> None:
        """Add items to the front of the BatchRequest.

        This is intended to be used when objects should be retries, eg. after a temporary error.
        """
        self._lock.acquire()
        self._items = item + self._items
        self._lock.release()


class ReferencesBatchRequest(BatchRequest[_BatchReference, BatchReferenceReturn]):
    """Collect Weaviate-object references to add them in one request to Weaviate."""

    def pop_items(self, pop_amount: int, uuid_lookup: Set[str]) -> List[_BatchReference]:
        """Pop the given number of items from the BatchRequest queue.

        Returns
            `List[_BatchReference]` items from the BatchRequest.
        """
        ret: List[_BatchReference] = []
        i = 0
        self._lock.acquire()
        while len(ret) < pop_amount and len(self._items) > 0 and i < len(self._items):
            if self._items[i].from_uuid not in uuid_lookup and (
                self._items[i].to_uuid is None or self._items[i].to_uuid not in uuid_lookup
            ):
                ret.append(self._items.pop(i))
            else:
                i += 1
        self._lock.release()
        return ret


class ObjectsBatchRequest(BatchRequest[_BatchObject, BatchObjectReturn]):
    """Collect objects for one batch request to weaviate."""

    def pop_items(self, pop_amount: int) -> List[_BatchObject]:
        """Pop the given number of items from the BatchRequest queue.

        Returns
            `List[_BatchObject]` items from the BatchRequest.
        """
        self._lock.acquire()
        if pop_amount >= len(self._items):
            ret = copy(self._items)
            self._items.clear()
        else:
            ret = copy(self._items[:pop_amount])
            self._items = self._items[pop_amount:]

        self._lock.release()
        return ret


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
        event_loop: _EventLoop,
        vectorizer_batching: bool,
        objects_: Optional[ObjectsBatchRequest] = None,
        references: Optional[ReferencesBatchRequest] = None,
    ) -> None:
        self.__batch_objects = objects_ or ObjectsBatchRequest()
        self.__batch_references = references or ReferencesBatchRequest()
        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = consistency_level
        self.__vectorizer_batching = vectorizer_batching

        self.__batch_grpc = _BatchGRPC(connection, self.__consistency_level)
        self.__batch_rest = _BatchREST(connection, self.__consistency_level)

        # lookup table for objects that are currently being processed - is used to not send references from objects that have not been added yet
        self.__uuid_lookup_lock = threading.Lock()
        self.__uuid_lookup: Set[str] = set()

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__results_lock = threading.Lock()

        self.__cluster = _ClusterBatch(self.__connection)

        self.__batching_mode: _BatchMode = batch_mode
        self.__max_batch_size: int = 1000

        self.__loop = event_loop
        self.__objs_count = 0
        self.__objs_logs_count = 0
        self.__refs_logs_count = 0

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
        elif isinstance(self.__batching_mode, _DynamicBatching) and not self.__vectorizer_batching:
            self.__recommended_num_objects = 10
            self.__concurrent_requests = 2
        else:
            assert isinstance(self.__batching_mode, _DynamicBatching) and self.__vectorizer_batching
            self.__recommended_num_objects = VECTORIZER_BATCHING_STEP_SIZE
            self.__concurrent_requests = 2
            self.__dynamic_batching_sleep_time: int = 0
            self._batch_send: bool = False

        self.__recommended_num_refs: int = 50

        self.__active_requests = 0
        self.__active_requests_lock = threading.Lock()

        # dynamic batching
        self.__time_last_scale_up: float = 0
        self.__rate_queue: deque = deque(maxlen=50)  # 5s with 0.1s refresh rate
        self.__took_queue: deque = deque(maxlen=CONCURRENT_REQUESTS_DYNAMIC_VECTORIZER)

        # fixed rate batching
        self.__time_stamp_last_request: float = 0
        # do 62 secs to give us some buffer to the "per-minute" calculation
        self.__fix_rate_batching_base_time = 62

        self.__bg_thread = self.__start_bg_threads()
        self.__bg_thread_exception: Optional[Exception] = None

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

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

    def __batch_send(self) -> None:
        refresh_time: float = 0.01
        while (
            self.__shut_background_thread_down is not None
            and not self.__shut_background_thread_down.is_set()
        ):
            if isinstance(self.__batching_mode, _RateLimitedBatching):
                if (
                    time.time() - self.__time_stamp_last_request
                    < self.__fix_rate_batching_base_time // self.__concurrent_requests
                ):
                    time.sleep(1)
                    continue
                refresh_time = 0
            elif isinstance(self.__batching_mode, _DynamicBatching) and self.__vectorizer_batching:
                if self.__dynamic_batching_sleep_time > 0:
                    if (
                        time.time() - self.__time_stamp_last_request
                        < self.__dynamic_batching_sleep_time
                    ):
                        time.sleep(1)
                        continue

            if (
                self.__active_requests < self.__concurrent_requests
                and len(self.__batch_objects) + len(self.__batch_references) > 0
            ):
                self.__time_stamp_last_request = time.time()

                self._batch_send = True
                self.__active_requests_lock.acquire()
                self.__active_requests += 1
                self.__active_requests_lock.release()

                objs = self.__batch_objects.pop_items(self.__recommended_num_objects)
                self.__uuid_lookup_lock.acquire()
                refs = self.__batch_references.pop_items(
                    self.__recommended_num_refs, uuid_lookup=self.__uuid_lookup
                )
                self.__uuid_lookup_lock.release()
                # do not block the thread - the results are written to a central (locked) list and we want to have multiple concurrent batch-requests
                self.__loop.schedule(
                    self.__send_batch,
                    objs,
                    refs,
                    readd_rate_limit=isinstance(self.__batching_mode, _RateLimitedBatching),
                )

            time.sleep(refresh_time)

    def __dynamic_batch_rate_loop(self) -> None:
        refresh_time = 1
        while (
            self.__shut_background_thread_down is not None
            and not self.__shut_background_thread_down.is_set()
        ):
            if not isinstance(self.__batching_mode, _DynamicBatching):
                return

            try:
                self.__dynamic_batching()
            except Exception as e:
                _Warnings.batch_refresh_failed(repr(e))

            time.sleep(refresh_time)

    def __start_bg_threads(self) -> threading.Thread:
        """Create a background thread that periodically checks how congested the batch queue is."""
        self.__shut_background_thread_down = threading.Event()

        def dynamic_batch_rate_wrapper() -> None:
            try:
                self.__dynamic_batch_rate_loop()
            except Exception as e:
                self.__bg_thread_exception = e

        demonDynamic = threading.Thread(
            target=dynamic_batch_rate_wrapper,
            daemon=True,
            name="BgDynamicBatchRate",
        )
        demonDynamic.start()

        def batch_send_wrapper() -> None:
            try:
                self.__batch_send()
            except Exception as e:
                self.__bg_thread_exception = e

        demonBatchSend = threading.Thread(
            target=batch_send_wrapper,
            daemon=True,
            name="BgBatchScheduler",
        )
        demonBatchSend.start()
        return demonBatchSend

    def __dynamic_batching(self) -> None:
        status = self.__loop.run_until_complete(self.__cluster.get_nodes_status)
        if "batchStats" not in status[0] or "queueLength" not in status[0]["batchStats"]:
            # async indexing - just send a lot
            self.__batching_mode = _FixedSizeBatching(1000, 10)
            self.__recommended_num_objects = 1000
            self.__concurrent_requests = 10
            return

        rate: int = status[0]["batchStats"]["ratePerSecond"]
        rate_per_worker = rate / self.__concurrent_requests

        batch_length = status[0]["batchStats"]["queueLength"]

        self.__rate_queue.append(rate)

        if self.__vectorizer_batching:
            # slow vectorizer, we want to send larger batches that can take a bit longer, but fewer of them. We might need to sleep
            if len(self.__took_queue) > 0 and self._batch_send:
                max_took = max(self.__took_queue)
                self.__dynamic_batching_sleep_time = 0
                if max_took > 2 * BATCH_TIME_TARGET:
                    self.__concurrent_requests = 1
                    self.__recommended_num_objects = VECTORIZER_BATCHING_STEP_SIZE
                elif max_took > BATCH_TIME_TARGET:
                    current_step = self.__recommended_num_objects // VECTORIZER_BATCHING_STEP_SIZE

                    if self.__concurrent_requests > 1:
                        self.__concurrent_requests -= 1
                    elif current_step > 1:
                        self.__recommended_num_objects = VECTORIZER_BATCHING_STEP_SIZE * (
                            current_step - 1
                        )
                    else:
                        # cannot scale down, sleep a bit
                        self.__dynamic_batching_sleep_time = max_took - BATCH_TIME_TARGET

                elif max_took < 3 * BATCH_TIME_TARGET // 4:
                    if self.__dynamic_batching_sleep_time > 0:
                        self.__dynamic_batching_sleep_time = 0
                    elif self.__concurrent_requests < 3:
                        self.__concurrent_requests += 1
                    else:
                        current_step = (
                            self.__recommended_num_objects // VECTORIZER_BATCHING_STEP_SIZE
                        )
                        self.__recommended_num_objects = VECTORIZER_BATCHING_STEP_SIZE * (
                            current_step + 1
                        )
                self._batch_send = False
        else:
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

    async def __send_batch(
        self, objs: List[_BatchObject], refs: List[_BatchReference], readd_rate_limit: bool
    ) -> None:
        if (n_objs := len(objs)) > 0:
            start = time.time()
            try:
                response_obj = await self.__batch_grpc.objects(
                    objects=objs, timeout=DEFAULT_REQUEST_TIMEOUT
                )
            except Exception as e:
                errors_obj = {
                    idx: ErrorObject(message=repr(e), object_=obj) for idx, obj in enumerate(objs)
                }
                response_obj = BatchObjectReturn(
                    _all_responses=list(errors_obj.values()),
                    elapsed_seconds=time.time() - start,
                    errors=errors_obj,
                    has_errors=True,
                )

            readded_uuids = set()
            readded_objects = []
            highest_retry_count = 0
            for i, err in response_obj.errors.items():
                if (
                    (
                        "support@cohere.com" in err.message
                        and (
                            "rate limit" in err.message
                            or "500 error: internal server error" in err.message
                        )
                    )
                    or (
                        "OpenAI" in err.message
                        and (
                            "Rate limit reached" in err.message
                            or "on tokens per min (TPM)" in err.message
                            or "503 error: Service Unavailable." in err.message
                            or "500 error: The server had an error while processing your request."
                            in err.message
                        )
                    )
                    or ("failed with status: 503 error" in err.message)  # huggingface
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

                readd_objects = [
                    err.object_ for i, err in response_obj.errors.items() if i in readded_objects
                ]
                readded_uuids = {obj.uuid for obj in readd_objects}

                self.__batch_objects.prepend(readd_objects)

                new_errors = {
                    i: err for i, err in response_obj.errors.items() if i not in readded_objects
                }
                response_obj = BatchObjectReturn(
                    uuids={
                        i: uid for i, uid in response_obj.uuids.items() if i not in readded_objects
                    },
                    errors=new_errors,
                    has_errors=len(new_errors) > 0,
                    _all_responses=[
                        err
                        for i, err in enumerate(response_obj.all_responses)
                        if i not in readded_objects
                    ],
                    elapsed_seconds=response_obj.elapsed_seconds,
                )
                if readd_rate_limit:
                    # for rate limited batching the timing is handled by the outer loop => no sleep here
                    self.__time_stamp_last_request = (
                        time.time() + self.__fix_rate_batching_base_time * (highest_retry_count + 1)
                    )  # skip a full minute to recover from the rate limit
                    self.__fix_rate_batching_base_time += (
                        1  # increase the base time as the current one is too low
                    )
                else:
                    # sleep a bit to recover from the rate limit in other cases
                    time.sleep(2**highest_retry_count)
            self.__uuid_lookup_lock.acquire()
            self.__uuid_lookup.difference_update(
                obj.uuid for obj in objs if obj.uuid not in readded_uuids
            )
            self.__uuid_lookup_lock.release()

            if (n_obj_errs := len(response_obj.errors)) > 0 and self.__objs_logs_count < 30:
                logger.error(
                    {
                        "message": f"Failed to send {n_obj_errs} objects in a batch of {n_objs}. Please inspect client.batch.failed_objects or collection.batch.failed_objects for the failed objects.",
                    }
                )
                self.__objs_logs_count += 1
            if self.__objs_logs_count > 30:
                logger.error(
                    {
                        "message": "There have been more than 30 failed object batches. Further errors will not be logged.",
                    }
                )
            self.__results_lock.acquire()
            self.__results_for_wrapper.results.objs += response_obj
            self.__results_for_wrapper.failed_objects.extend(response_obj.errors.values())
            self.__results_lock.release()
            self.__took_queue.append(time.time() - start)

        if (n_refs := len(refs)) > 0:
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
            if (n_ref_errs := len(response_ref.errors)) > 0 and self.__refs_logs_count < 30:
                logger.error(
                    {
                        "message": f"Failed to send {n_ref_errs} references in a batch of {n_refs}. Please inspect client.batch.failed_references or collection.batch.failed_references for the failed references.",
                        "errors": response_ref.errors,
                    }
                )
                self.__refs_logs_count += 1
            if self.__refs_logs_count > 30:
                logger.error(
                    {
                        "message": "There have been more than 30 failed reference batches. Further errors will not be logged.",
                    }
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
        vector: Optional[VECTORS] = None,
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
                index=self.__objs_count,
            )
            self.__objs_count += 1
            self.__results_for_wrapper.imported_shards.add(
                Shard(collection=collection, tenant=tenant)
            )
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        self.__uuid_lookup_lock.acquire()
        self.__uuid_lookup.add(str(batch_object.uuid))
        self.__uuid_lookup_lock.release()
        self.__batch_objects.add(batch_object._to_internal())

        # block if queue gets too long or weaviate is overloaded - reading files is faster them sending them so we do
        # not need a long queue
        while (
            self.__recommended_num_objects == 0
            or len(self.__batch_objects) >= self.__recommended_num_objects * 2
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


class _ClusterBatch:
    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    async def get_nodes_status(
        self,
    ) -> List[Node]:
        try:
            response = await self._connection.get(path="/nodes")
        except ConnectError as conn_err:
            raise ConnectError("Get nodes status failed due to connection error") from conn_err

        response_typed = _decode_json_response_dict(response, "Nodes status")
        assert response_typed is not None
        nodes = response_typed.get("nodes")
        if nodes is None or nodes == []:
            raise EmptyResponseException("Nodes status response returned empty")
        return cast(List[Node], nodes)

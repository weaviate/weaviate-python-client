import contextvars
import functools
import math
import os
import threading
import time
import uuid as uuid_package
from abc import ABC
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Dict, Generator, Generic, List, Optional, Set, TypeVar, Union, cast

from httpx import ConnectError
from pydantic import ValidationError
from typing_extensions import TypeAlias

from weaviate.cluster.types import Node
from weaviate.collections.batch.grpc_batch import _BatchGRPC
from weaviate.collections.batch.rest import _BatchREST
from weaviate.collections.classes.batch import (
    BatchObject,
    BatchObjectReturn,
    BatchReference,
    BatchReferenceReturn,
    BatchResult,
    ErrorObject,
    ErrorReference,
    Shard,
    _BatchObject,
    _BatchReference,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import (
    ReferenceInput,
    ReferenceInputs,
    ReferenceToMulti,
)
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.exceptions import (
    EmptyResponseException,
    WeaviateBatchStreamError,
    WeaviateBatchValidationError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
)
from weaviate.logger import logger
from weaviate.proto.v1 import batch_pb2
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
MAX_RETRIES = float(
    os.getenv("WEAVIATE_BATCH_MAX_RETRIES", "9.299")
)  # approximately 10m30s of waiting in worst case, e.g. server scale up event


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


Ref = TypeVar("Ref", bound=Union[_BatchReference, batch_pb2.BatchReference])


class ReferencesBatchRequest(BatchRequest[Ref, BatchReferenceReturn]):
    """Collect Weaviate-object references to add them in one request to Weaviate."""

    def pop_items(self, pop_amount: int, uuid_lookup: Set[str]) -> List[Ref]:
        """Pop the given number of items from the BatchRequest queue.

        Returns:
            A list of items from the BatchRequest.
        """
        ret: List[Ref] = []
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

    def head(self) -> Optional[Ref]:
        """Get the first item from the BatchRequest queue without removing it.

        Returns:
            The first item from the BatchRequest or None if the queue is empty.
        """
        self._lock.acquire()
        item = self._items[0] if len(self._items) > 0 else None
        self._lock.release()
        return item


Obj = TypeVar("Obj", bound=Union[_BatchObject, batch_pb2.BatchObject])


class ObjectsBatchRequest(Generic[Obj], BatchRequest[Obj, BatchObjectReturn]):
    """Collect objects for one batch request to weaviate."""

    def pop_items(self, pop_amount: int) -> List[Obj]:
        """Pop the given number of items from the BatchRequest queue.

        Returns:
            A list of items from the BatchRequest.
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

    def head(self) -> Optional[Obj]:
        """Get the first item from the BatchRequest queue without removing it.

        Returns:
            The first item from the BatchRequest or None if the queue is empty.
        """
        self._lock.acquire()
        item = self._items[0] if len(self._items) > 0 else None
        self._lock.release()
        return item


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


@dataclass
class _ServerSideBatching:
    concurrency: int


_BatchMode: TypeAlias = Union[
    _DynamicBatching, _FixedSizeBatching, _RateLimitedBatching, _ServerSideBatching
]


class _BatchBase:
    def __init__(
        self,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        batch_mode: _BatchMode,
        executor: ThreadPoolExecutor,
        vectorizer_batching: bool,
        objects: Optional[ObjectsBatchRequest] = None,
        references: Optional[ReferencesBatchRequest] = None,
    ) -> None:
        self.__batch_objects = objects or ObjectsBatchRequest()
        self.__batch_references = references or ReferencesBatchRequest()

        self.__connection = connection
        self.__consistency_level: Optional[ConsistencyLevel] = consistency_level
        self.__vectorizer_batching = vectorizer_batching

        self.__batch_grpc = _BatchGRPC(
            connection._weaviate_version, self.__consistency_level, connection._grpc_max_msg_size
        )
        self.__batch_rest = _BatchREST(self.__consistency_level)

        # lookup table for objects that are currently being processed - is used to not send references from objects that have not been added yet
        self.__uuid_lookup: Set[str] = set()

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__cluster = _ClusterBatch(self.__connection)

        self.__batching_mode: _BatchMode = batch_mode
        self.__max_batch_size: int = 1000

        self.__executor = executor
        self.__objs_count = 0
        self.__refs_count = 0
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

        # dynamic batching
        self.__time_last_scale_up: float = 0
        self.__rate_queue: deque = deque(maxlen=50)  # 5s with 0.1s refresh rate
        self.__took_queue: deque = deque(maxlen=CONCURRENT_REQUESTS_DYNAMIC_VECTORIZER)

        # fixed rate batching
        self.__time_stamp_last_request: float = 0
        # do 62 secs to give us some buffer to the "per-minute" calculation
        self.__fix_rate_batching_base_time = 62

        self.__active_requests_lock = threading.Lock()
        self.__uuid_lookup_lock = threading.Lock()
        self.__results_lock = threading.Lock()

        self.__bg_thread = self.__start_bg_threads()
        self.__bg_thread_exception: Optional[Exception] = None

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

    def _start(self):
        pass

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
                with self.__active_requests_lock:
                    self.__active_requests += 1

                start = time.time()
                while (len_o := len(self.__batch_objects)) < self.__recommended_num_objects and (
                    len_r := len(self.__batch_references)
                ) < self.__recommended_num_refs:
                    # wait for more objects to be added up to the recommended number
                    time.sleep(0.01)
                    if (
                        self.__shut_background_thread_down is not None
                        and self.__shut_background_thread_down.is_set()
                    ):
                        # shutdown was requested, exit the loop
                        break
                    if time.time() - start >= 1 and (
                        len_o == len(self.__batch_objects) or len_r == len(self.__batch_references)
                    ):
                        # no new objects were added in the last second, exit the loop
                        break

                objs = self.__batch_objects.pop_items(self.__recommended_num_objects)
                refs = self.__batch_references.pop_items(
                    self.__recommended_num_refs,
                    uuid_lookup=self.__uuid_lookup,
                )
                # do not block the thread - the results are written to a central (locked) list and we want to have multiple concurrent batch-requests
                ctx = contextvars.copy_context()
                self.__executor.submit(
                    ctx.run,
                    functools.partial(
                        self.__send_batch,
                        objs,
                        refs,
                        readd_rate_limit=isinstance(self.__batching_mode, _RateLimitedBatching),
                    ),
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
                logger.debug(repr(e))

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
                logger.error(e)
                self.__bg_thread_exception = e

        demonBatchSend = threading.Thread(
            target=batch_send_wrapper,
            daemon=True,
            name="BgBatchScheduler",
        )
        demonBatchSend.start()

        return demonBatchSend

    def __dynamic_batching(self) -> None:
        status = self.__cluster.get_nodes_status()
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

    def __send_batch(
        self,
        objs: List[_BatchObject],
        refs: List[_BatchReference],
        readd_rate_limit: bool,
    ) -> None:
        if (n_objs := len(objs)) > 0:
            start = time.time()
            try:
                response_obj = executor.result(
                    self.__batch_grpc.objects(
                        connection=self.__connection,
                        objects=objs,
                        timeout=DEFAULT_REQUEST_TIMEOUT,
                        max_retries=MAX_RETRIES,
                    )
                )
                if response_obj.has_errors:
                    logger.error(
                        {
                            "message": f"Failed to send {len(response_obj.errors)} in a batch of {len(objs)}",
                            "errors": {err.message for err in response_obj.errors.values()},
                        }
                    )
            except Exception as e:
                errors_obj = {
                    idx: ErrorObject(message=repr(e), object_=BatchObject._from_internal(obj))
                    for idx, obj in enumerate(objs)
                }
                logger.error(
                    {
                        "message": f"Failed to send all objects in a batch of {len(objs)}",
                        "error": repr(e),
                    }
                )
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
                    err.object_._to_internal()
                    for i, err in response_obj.errors.items()
                    if i in readded_objects
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
            with self.__uuid_lookup_lock:
                self.__uuid_lookup.difference_update(
                    obj.uuid for obj in objs if obj.uuid not in readded_uuids
                )

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
            with self.__results_lock:
                self.__results_for_wrapper.results.objs += response_obj
                self.__results_for_wrapper.failed_objects.extend(response_obj.errors.values())
            self.__took_queue.append(time.time() - start)

        if (n_refs := len(refs)) > 0:
            start = time.time()
            try:
                response_ref = executor.result(
                    self.__batch_rest.references(connection=self.__connection, references=refs)
                )
            except Exception as e:
                errors_ref = {
                    idx: ErrorReference(
                        message=repr(e), reference=BatchReference._from_internal(ref)
                    )
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
            with self.__results_lock:
                self.__results_for_wrapper.results.refs += response_ref
                self.__results_for_wrapper.failed_references.extend(response_ref.errors.values())

        with self.__active_requests_lock:
            self.__active_requests -= 1

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
        self.__uuid_lookup.add(str(batch_object.uuid))
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
                    index=self.__refs_count,
                )
                self.__refs_count += 1
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


class _BgThreads:
    def __init__(self, send: threading.Thread, recv: threading.Thread):
        self.send = send
        self.recv = recv
        self.__started_recv = False
        self.__started_send = False

    def start_recv(self) -> None:
        if not self.__started_recv:
            self.recv.start()
            self.__started_recv = True

    def start_send(self) -> None:
        if not self.__started_send:
            self.send.start()
            self.__started_send = True

    def is_alive(self) -> bool:
        """Check if the background threads are still alive."""
        return self.send_alive() or self.recv_alive()

    def send_alive(self) -> bool:
        """Check if the send background thread is still alive."""
        return self.send.is_alive()

    def recv_alive(self) -> bool:
        """Check if the recv background thread is still alive."""
        return self.recv.is_alive()


class _BatchBaseNew:
    def __init__(
        self,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        batch_mode: _BatchMode,
        executor: ThreadPoolExecutor,
        vectorizer_batching: bool,
        objects: Optional[ObjectsBatchRequest[batch_pb2.BatchObject]] = None,
        references: Optional[ReferencesBatchRequest] = None,
    ) -> None:
        self.__batch_objects = objects or ObjectsBatchRequest[batch_pb2.BatchObject]()
        self.__batch_references = references or ReferencesBatchRequest[batch_pb2.BatchReference]()

        self.__connection = connection
        self.__consistency_level: ConsistencyLevel = consistency_level or ConsistencyLevel.QUORUM
        self.__batch_size = 100

        self.__batch_grpc = _BatchGRPC(
            connection._weaviate_version, self.__consistency_level, connection._grpc_max_msg_size
        )

        # lookup table for objects that are currently being processed - is used to not send references from objects that have not been added yet
        self.__uuid_lookup: Set[str] = set()

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__objs_count = 0
        self.__refs_count = 0

        self.__uuid_lookup_lock = threading.Lock()
        self.__results_lock = threading.Lock()

        self.__bg_thread_exception: Optional[Exception] = None
        self.__is_shutting_down = threading.Event()
        self.__is_shutdown = threading.Event()

        self.__objs_cache_lock = threading.Lock()
        self.__refs_cache_lock = threading.Lock()
        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache: dict[int, BatchReference] = {}

        # maxsize=1 so that __batch_send does not run faster than generator for __batch_recv
        # thereby using too much buffer in case of server-side shutdown
        self.__reqs: Queue[Optional[batch_pb2.BatchStreamRequest]] = Queue(maxsize=1)

        self.__stop = False

        self.__batch_mode = batch_mode

        self.__total = 0

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

    def __all_threads_alive(self) -> bool:
        return self.__bg_threads is not None and all(
            thread.is_alive() for thread in self.__bg_threads
        )

    def __any_threads_alive(self) -> bool:
        return self.__bg_threads is not None and any(
            thread.is_alive() for thread in self.__bg_threads
        )

    def _start(self) -> None:
        assert isinstance(self.__batch_mode, _ServerSideBatching), (
            "Only server-side batching is supported in this mode"
        )
        self.__bg_threads = [
            self.__start_bg_threads() for _ in range(self.__batch_mode.concurrency)
        ]
        logger.warning(
            f"Provisioned {len(self.__bg_threads)} stream(s) to the server for batch processing"
        )
        now = time.time()
        while not self.__all_threads_alive():
            # wait for the stream to be started by __batch_stream
            time.sleep(0.01)
            if time.time() - now > 10:
                raise WeaviateBatchValidationError(
                    "Batch stream was not started within 10 seconds. Please check your connection."
                )

    def _shutdown(self) -> None:
        # Shutdown the current batch and wait for all requests to be finished
        self.flush()
        self.__stop = True

        # we are done, wait for bg threads to finish
        # self.__batch_stream will set the shutdown event when it receives
        # the stop message from the server
        while self.__any_threads_alive():
            time.sleep(1)
        logger.warning("Send & receive threads finished.")

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
            if len(self.__batch_objects) + len(self.__batch_references) > 0:
                self._batch_send = True
                start = time.time()
                while (len_o := len(self.__batch_objects)) + (
                    len_r := len(self.__batch_references)
                ) < self.__batch_size:
                    # wait for more objects to be added up to the batch size
                    time.sleep(0.01)
                    if (
                        self.__shut_background_thread_down is not None
                        and self.__shut_background_thread_down.is_set()
                    ):
                        logger.warning("Threads were shutdown, exiting batch send loop")
                        # shutdown was requested, exit early
                        self.__reqs.put(None)
                        return
                    if time.time() - start >= 1 and (
                        len_o == len(self.__batch_objects) or len_r == len(self.__batch_references)
                    ):
                        # no new objects were added in the last second, exit the loop
                        break

                objs = self.__batch_objects.pop_items(self.__batch_size)
                refs = self.__batch_references.pop_items(
                    self.__batch_size - len(objs),
                    uuid_lookup=self.__uuid_lookup,
                )
                with self.__uuid_lookup_lock:
                    self.__uuid_lookup.difference_update(obj.uuid for obj in objs)

                for req in self.__generate_stream_requests(objs, refs):
                    logged = False
                    while self.__is_shutting_down.is_set() or self.__is_shutdown.is_set():
                        # if we were shutdown by the node we were connected to, we need to wait for the stream to be restarted
                        # so that the connection is refreshed to a new node where the objects can be accepted
                        # otherwise, we wait until the stream has been started by __batch_stream to send the first batch
                        if not logged:
                            logger.warning("Waiting for stream to be re-established...")
                            logged = True
                            # put sentinel into our queue to signal the end of the current stream
                            self.__reqs.put(None)
                        time.sleep(1)
                    if logged:
                        logger.warning("Stream re-established, resuming sending batches")
                    self.__reqs.put(req)
            elif self.__stop:
                # we are done, send the sentinel into our queue to be consumed by the batch sender
                self.__reqs.put(None)  # signal the end of the stream
                logger.warning("Batching finished, sent stop signal to batch stream")
                return
            time.sleep(refresh_time)

    def __generate_stream_requests(
        self,
        objs: List[batch_pb2.BatchObject],
        refs: List[batch_pb2.BatchReference],
    ) -> Generator[batch_pb2.BatchStreamRequest, None, None]:
        per_object_overhead = 4  # extra overhead bytes per object in the request

        def request_maker():
            return batch_pb2.BatchStreamRequest()

        request = request_maker()
        total_size = request.ByteSize()

        for obj in objs:
            obj_size = obj.ByteSize() + per_object_overhead

            if total_size + obj_size >= self.__batch_grpc.grpc_max_msg_size:
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.objects.values.append(obj)
            total_size += obj_size

        for ref in refs:
            ref_size = ref.ByteSize() + per_object_overhead

            if total_size + ref_size >= self.__batch_grpc.grpc_max_msg_size:
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.references.values.append(ref)
            total_size += ref_size

        if len(request.data.objects.values) > 0 or len(request.data.references.values) > 0:
            yield request

    def __generate_stream_requests_for_grpc(
        self,
    ) -> Generator[batch_pb2.BatchStreamRequest, None, None]:
        yield batch_pb2.BatchStreamRequest(
            start=batch_pb2.BatchStreamRequest.Start(
                consistency_level=self.__batch_grpc._consistency_level,
            ),
        )
        while (
            self.__shut_background_thread_down is not None
            and not self.__shut_background_thread_down.is_set()
        ):
            req = self.__reqs.get()
            if req is not None:
                self.__total += len(req.data.objects.values) + len(req.data.references.values)
                yield req
                continue
            if self.__stop and not (
                self.__is_shutting_down.is_set() or self.__is_shutdown.is_set()
            ):
                logger.warning("Batching finished, closing the client-side of the stream")
                yield batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop())
                return
            if self.__is_shutting_down.is_set():
                logger.warning("Server shutting down, closing the client-side of the stream")
                return
            logger.warning("Received sentinel, but not stopping, continuing...")

    def __batch_recv(self) -> None:
        for message in self.__batch_grpc.stream(
            connection=self.__connection,
            requests=self.__generate_stream_requests_for_grpc(),
        ):
            if message.HasField("started"):
                logger.warning("Batch stream started successfully")
                for threads in self.__bg_threads:
                    threads.start_send()
            if message.HasField("backoff"):
                if (
                    message.backoff.batch_size != self.__batch_size
                    and not self.__is_shutting_down.is_set()
                    and not self.__is_shutdown.is_set()
                    and not self.__stop
                ):
                    self.__batch_size = message.backoff.batch_size
                    logger.warning(
                        f"Updated batch size to {self.__batch_size} as per server request"
                    )
            if message.HasField("results"):
                result_objs = BatchObjectReturn()
                # result_refs = BatchReferenceReturn()
                failed_objs: List[ErrorObject] = []
                failed_refs: List[ErrorReference] = []
                for error in message.results.errors:
                    if error.HasField("uuid"):
                        try:
                            cached = self.__objs_cache.pop(error.uuid)
                        except KeyError:
                            continue
                        err = ErrorObject(
                            message=error.error,
                            object_=cached,
                        )
                        result_objs += BatchObjectReturn(
                            _all_responses=[err],
                            errors={cached.index: err},
                        )
                        failed_objs.append(err)
                        logger.warning(
                            {
                                "error": error.error,
                                "object": error.uuid,
                                "action": "use {client,collection}.batch.failed_objects to access this error",
                            }
                        )
                    if error.HasField("beacon"):
                        # TODO: get cached ref from beacon
                        err = ErrorReference(
                            message=error.error,
                            reference=error.beacon,  # pyright: ignore
                        )
                        failed_refs.append(err)
                        logger.warning(
                            {
                                "error": error.error,
                                "reference": error.beacon,
                                "action": "use {client,collection}.batch.failed_references to access this error",
                            }
                        )
                for success in message.results.successes:
                    if success.HasField("uuid"):
                        try:
                            cached = self.__objs_cache.pop(success.uuid)
                        except KeyError:
                            continue
                        uuid = uuid_package.UUID(success.uuid)
                        result_objs += BatchObjectReturn(
                            _all_responses=[uuid],
                            uuids={cached.index: uuid},
                        )
                    if success.HasField("beacon"):
                        # TODO: remove cached ref using beacon
                        # self.__refs_cache.pop(success.beacon, None)
                        pass
                with self.__results_lock:
                    self.__results_for_wrapper.results.objs += result_objs
                    self.__results_for_wrapper.failed_objects.extend(failed_objs)
                    self.__results_for_wrapper.failed_references.extend(failed_refs)
            elif message.HasField("shutting_down"):
                logger.warning(
                    "Received shutting down message from server, pausing sending until stream is re-established"
                )
                self.__is_shutting_down.set()
            elif message.HasField("shutdown"):
                logger.warning("Received shutdown finished message from server")
                self.__is_shutdown.set()
                self.__is_shutting_down.clear()
                self.__reconnect()

        # restart the stream if we were shutdown by the node we were connected to ensuring that the index is
        # propagated properly from it to the new one
        if self.__is_shutdown.is_set():
            logger.warning("Restarting batch recv after shutdown...")
            self.__is_shutdown.clear()
            return self.__batch_recv()
        else:
            logger.warning("Server closed the stream from its side, shutting down batch")
            return

    def __reconnect(self, retry: int = 0) -> None:
        try:
            logger.warning(f"Trying to reconnect after shutdown... {retry + 1}/{5}")
            self.__connection.close("sync")
            self.__connection.connect(force=True)
            logger.warning("Reconnected successfully")
        except (WeaviateStartUpError, WeaviateGRPCUnavailableError) as e:
            if retry < 5:
                time.sleep(2**retry)
                self.__reconnect(retry + 1)
            else:
                logger.error("Failed to reconnect after 5 attempts")
                self.__bg_thread_exception = e

    def __start_bg_threads(self) -> _BgThreads:
        """Create a background thread that periodically checks how congested the batch queue is."""
        self.__shut_background_thread_down = threading.Event()

        def batch_send_wrapper() -> None:
            try:
                self.__batch_send()
                logger.warning("exited batch send thread")
            except Exception as e:
                logger.error(e)
                self.__bg_thread_exception = e

        def batch_recv_wrapper() -> None:
            socket_hung_up = False
            try:
                self.__batch_recv()
                logger.warning("exited batch receive thread")
            except Exception as e:
                if isinstance(e, WeaviateBatchStreamError) and (
                    "Socket closed" in e.message or "context canceled" in e.message
                ):
                    socket_hung_up = True
                else:
                    logger.error(e)
                    logger.error(type(e))
                    self.__bg_thread_exception = e
            if socket_hung_up:
                # this happens during ungraceful shutdown of the coordinator
                # lets restart the stream and add the cached objects again
                logger.warning("Stream closed unexpectedly, restarting...")
                self.__reconnect()
                # server sets this whenever it restarts, gracefully or unexpectedly, so need to clear it now
                self.__is_shutting_down.clear()
                with self.__objs_cache_lock:
                    logger.warning(
                        f"Re-adding {len(self.__objs_cache)} cached objects to the batch"
                    )
                    self.__batch_objects.prepend(
                        [
                            self.__batch_grpc.grpc_object(o._to_internal())
                            for o in self.__objs_cache.values()
                        ]
                    )
                with self.__refs_cache_lock:
                    self.__batch_references.prepend(
                        [
                            self.__batch_grpc.grpc_reference(o._to_internal())
                            for o in self.__refs_cache.values()
                        ]
                    )
                # start a new stream with a newly reconnected channel
                return batch_recv_wrapper()

        threads = _BgThreads(
            send=threading.Thread(
                target=batch_send_wrapper,
                daemon=True,
                name="BgBatchSend",
            ),
            recv=threading.Thread(
                target=batch_recv_wrapper,
                daemon=True,
                name="BgBatchRecv",
            ),
        )
        threads.start_recv()
        return threads

    def flush(self) -> None:
        """Flush the batch queue and wait for all requests to be finished."""
        # bg thread is sending objs+refs automatically, so simply wait for everything to be done
        while len(self.__batch_objects) > 0 or len(self.__batch_references) > 0:
            time.sleep(0.01)
            self.__check_bg_threads_alive()

    def _add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[str] = None,
    ) -> UUID:
        self.__check_bg_threads_alive()
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
            self.__results_for_wrapper.imported_shards.add(
                Shard(collection=collection, tenant=tenant)
            )
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        uuid = str(batch_object.uuid)
        with self.__uuid_lookup_lock:
            self.__uuid_lookup.add(uuid)
        self.__batch_objects.add(self.__batch_grpc.grpc_object(batch_object._to_internal()))
        with self.__objs_cache_lock:
            self.__objs_cache[uuid] = batch_object
        self.__objs_count += 1

        # block if queue gets too long or weaviate is overloaded - reading files is faster them sending them so we do
        # not need a long queue
        while len(self.__batch_objects) >= self.__batch_size * 2:
            self.__check_bg_threads_alive()
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
        self.__check_bg_threads_alive()
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
                    index=self.__refs_count,
                )
            except ValidationError as e:
                raise WeaviateBatchValidationError(repr(e))
            self.__batch_references.add(
                self.__batch_grpc.grpc_reference(batch_reference._to_internal())
            )
            with self.__refs_cache_lock:
                self.__refs_cache[self.__refs_count] = batch_reference
                self.__refs_count += 1

    def __check_bg_threads_alive(self) -> None:
        if self.__any_threads_alive():
            return

        raise self.__bg_thread_exception or Exception("Batch thread died unexpectedly")


class _ClusterBatch:
    def __init__(self, connection: ConnectionSync):
        self._connection = connection

    def get_nodes_status(
        self,
    ) -> List[Node]:
        try:
            response = executor.result(self._connection.get(path="/nodes"))
        except ConnectError as conn_err:
            raise ConnectError("Get nodes status failed due to connection error") from conn_err

        response_typed = _decode_json_response_dict(response, "Nodes status")
        assert response_typed is not None
        nodes = response_typed.get("nodes")
        if nodes is None or nodes == []:
            raise EmptyResponseException("Nodes status response returned empty")
        return cast(List[Node], nodes)

import asyncio
import math
import threading
import time
from abc import ABC
from copy import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Sequence, Set, TypeVar, Union
import uuid as uuid_package

from pydantic import ValidationError
from requests import ReadTimeout
from requests.exceptions import HTTPError as RequestsHTTPError

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
    _Reference,
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


@dataclass
class _BatchDataWrapper:
    results: BatchResult = BatchResult()
    failed_objects: List[ErrorObject] = field(default_factory=list)
    failed_references: List[ErrorReference] = field(default_factory=list)
    imported_shards: Set[Shard] = field(default_factory=set)


class _BatchBase:
    def __init__(
        self,
        connection: ConnectionV4,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
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

        self.__results_for_wrapper = results
        self.__results_lock = threading.Lock()

        self.__retry_failed_objects: bool = False
        self.__retry_failed_references: bool = False

        self.__cluster = Cluster(self.__connection)

        self.__max_batch_size: int = 1000
        self.__dynamic_batching = fixed_batch_size is None
        self.__recommended_num_objects: int = (
            fixed_batch_size if fixed_batch_size is not None else 10
        )
        # there seems to be a bug with weaviate when sending > 50 refs at once
        self.__recommended_num_refs: int = 50

        self.__concurrent_requests: int = (
            fixed_concurrent_requests if fixed_concurrent_requests is not None else 2
        )
        self.__active_requests = 0
        self.__active_requests_lock = threading.Lock()
        self.__last_scale_up: float = 0
        self.__max_observed_rate: int = 0

        try:
            self.__loop = asyncio.get_running_loop()
        except RuntimeError:
            self.__loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.__loop)
        self.__shut_background_thread_down = threading.Event()

        event_loop = threading.Thread(
            target=self.__start_event_loop_thread,
            daemon=True,
            args=(self.__loop,),
            name="eventLoop",
        )
        event_loop.start()
        while not self.__loop.is_running():
            time.sleep(0.01)

        future = asyncio.run_coroutine_threadsafe(self.__connection.aopen(), self.__loop)
        future.result()  # Wait for self._connection.aopen() to finish

        self.__start_bg_thread()

    def __start_event_loop_thread(self, loop: asyncio.AbstractEventLoop) -> None:
        while (
            self.__shut_background_thread_down is not None
            and not self.__shut_background_thread_down.is_set()
        ):
            if loop.is_running():
                continue
            else:
                loop.run_forever()

    def __start_bg_thread(self) -> None:
        """Create a background process that periodically checks how congested the batch queue is."""

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
                            self.__recommended_num_objects = 1000
                            self.__concurrent_requests = 10
                            continue

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
                                and time.time() - self.__last_scale_up > 1
                            ):
                                self.__concurrent_requests += 1
                                self.__last_scale_up = time.time()

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

                                if self.__max_batch_size == self.__recommended_num_objects:
                                    self.__concurrent_requests += 1

                            elif ratio < 10:  # too high, scale down
                                self.__recommended_num_objects = math.floor(
                                    rate_per_worker * 2 / ratio
                                )

                                if (
                                    self.__recommended_num_objects < 100
                                    and self.__concurrent_requests > 2
                                ):
                                    self.__concurrent_requests -= 1

                            else:  # way too high, stop sending new batches
                                self.__recommended_num_objects = 0
                                self.__concurrent_requests = 2

                        refresh_time = 0.01
                    except (RequestsHTTPError, ReadTimeout):
                        refresh_time = 0.1
                    except Exception as e:
                        _Warnings.batch_refresh_failed(repr(e))
                        refresh_time = 10

                time.sleep(refresh_time)

        demon = threading.Thread(
            target=periodic_check,
            daemon=True,
            name="BgBatchScheduler",
        )
        demon.start()

    def __start_batch(self) -> None:
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
                ),
                self.__loop,
            )

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
            self.__results_for_wrapper.results.objs += response_obj
            self.__results_for_wrapper.failed_objects.extend(response_obj.errors.values())
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

    def _shutdown(self) -> None:
        """Shutdown the current batch and wait for all requests to be finished."""
        self.flush()

        # we are done, shut bg threads down and end the event loop
        self.__shut_background_thread_down.set()
        future = asyncio.run_coroutine_threadsafe(self.__connection.aclose(), self.__loop)
        future.result()  # Wait for self._connection.aclose() to finish
        self.__loop.stop()

    def _add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
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
            time.sleep(1)

        self.__start_batch()

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
        if isinstance(to, _Reference) or isinstance(to, ReferenceToMulti):
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
                    to_object_collection=to.target_collection
                    if isinstance(to, _Reference) and to.is_multi_target
                    else None,
                    to_object_uuid=uid,
                    tenant=tenant,
                )
            except ValidationError as e:
                raise WeaviateBatchValidationError(repr(e))
            self.__batch_references.add(batch_reference._to_internal())

        # block if queue gets too long or weaviate is overloaded
        while self.__recommended_num_objects == 0:
            time.sleep(1)  # block if weaviate is overloaded, also do not send any refs

        self.__start_batch()

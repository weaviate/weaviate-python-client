import threading
import time
import uuid as uuid_package
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Full, Queue
from typing import Generator, List, Optional, Set, Union

from pydantic import ValidationError

from weaviate.collections.batch.base import (
    GCP_STREAM_TIMEOUT,
    ObjectsBatchRequest,
    ReferencesBatchRequest,
    _BatchDataWrapper,
    _BatchMode,
    _BgThreads,
    _ClusterBatch,
)
from weaviate.collections.batch.grpc_batch import _BatchGRPC
from weaviate.collections.classes.batch import (
    BatchObject,
    BatchObjectReturn,
    BatchReference,
    BatchReferenceReturn,
    ErrorObject,
    ErrorReference,
    Shard,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import (
    ReferenceInput,
    ReferenceInputs,
    ReferenceToMulti,
)
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect.executor import result
from weaviate.connect.v4 import ConnectionSync
from weaviate.exceptions import (
    WeaviateBatchFailedToReestablishStreamError,
    WeaviateBatchStreamError,
    WeaviateBatchValidationError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
)
from weaviate.logger import logger
from weaviate.proto.v1 import batch_pb2
from weaviate.types import UUID, VECTORS


class _BatchBaseSync:
    def __init__(
        self,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        batch_mode: Optional[_BatchMode] = None,
        executor: Optional[ThreadPoolExecutor] = None,
        vectorizer_batching: bool = False,
        objects: Optional[ObjectsBatchRequest[BatchObject]] = None,
        references: Optional[ReferencesBatchRequest[BatchReference]] = None,
    ) -> None:
        self.__batch_objects = objects or ObjectsBatchRequest[BatchObject]()
        self.__batch_references = references or ReferencesBatchRequest[BatchReference]()

        self.__connection = connection
        self.__is_gcp_on_wcd = connection._connection_params.is_gcp_on_wcd()
        self.__stream_start: Optional[float] = None
        self.__is_renewing_stream = threading.Event()
        self.__consistency_level: ConsistencyLevel = consistency_level or ConsistencyLevel.QUORUM
        self.__batch_size = 100

        self.__batch_grpc = _BatchGRPC(
            connection._weaviate_version, self.__consistency_level, connection._grpc_max_msg_size
        )
        self.__cluster = _ClusterBatch(self.__connection)
        self.__number_of_nodes = self.__cluster.get_number_of_nodes()

        # lookup table for objects that are currently being processed - is used to not send references from objects that have not been added yet
        self.__uuid_lookup: Set[str] = set()

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__objs_count = 0
        self.__refs_count = 0

        self.__uuid_lookup_lock = threading.Lock()
        self.__results_lock = threading.Lock()

        self.__bg_exception: Optional[Exception] = None
        self.__is_oom = threading.Event()
        self.__is_shutting_down = threading.Event()
        self.__is_shutdown = threading.Event()
        self.__is_hungup = threading.Event()
        self.__is_stopped = threading.Event()

        self.__shutdown_loop = threading.Event()
        self.__sent_sentinel = threading.Event()

        self.__objs_cache_lock = threading.Lock()
        self.__refs_cache_lock = threading.Lock()
        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache: dict[str, BatchReference] = {}

        self.__acks_lock = threading.Lock()
        self.__inflight_objs: set[str] = set()
        self.__inflight_refs: set[str] = set()

        # maxsize=1 so that __loop does not run faster than generator for __recv
        # thereby using too much buffer in case of server-side shutdown
        self.__reqs: Queue[Optional[batch_pb2.BatchStreamRequest]] = Queue(maxsize=1)

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

    def __all_threads_alive(self) -> bool:
        return self.__bg_threads.is_alive()

    def _start(self) -> None:
        self.__start_bg_threads()
        logger.info("Provisioned stream to the server for batch processing")
        now = time.time()
        while not self.__all_threads_alive():
            # wait for the recv threads to be started
            time.sleep(0.01)
            if time.time() - now > 60:
                raise WeaviateBatchStreamError(
                    "Batch stream was not started within 60 seconds. Please check your connection."
                )

    def _wait(self) -> None:
        self.__bg_threads.join()

        # copy the results to the public results
        self.__results_for_wrapper_backup.results = self.__results_for_wrapper.results
        self.__results_for_wrapper_backup.failed_objects = self.__results_for_wrapper.failed_objects
        self.__results_for_wrapper_backup.failed_references = (
            self.__results_for_wrapper.failed_references
        )
        self.__results_for_wrapper_backup.imported_shards = (
            self.__results_for_wrapper.imported_shards
        )

    def _shutdown(self) -> None:
        # Shutdown the current batch and wait for all requests to be finished
        self.__is_stopped.set()

    def __loop(self) -> None:
        refresh_time: float = 0.01
        while self.__bg_exception is None and not self.__shutdown_loop.is_set():
            if len(self.__batch_objects) + len(self.__batch_references) > 0:
                start = time.time()
                while (len_o := len(self.__batch_objects)) + (
                    len_r := len(self.__batch_references)
                ) < self.__batch_size:
                    # wait for more objects to be added up to the batch size
                    time.sleep(refresh_time)
                    if time.time() - start >= 1 and (
                        len_o == len(self.__batch_objects) or len_r == len(self.__batch_references)
                    ):
                        # no new objects were added in the last second, exit the loop
                        break

                objs = self.__batch_objects.pop_items(self.__batch_size)
                with self.__uuid_lookup_lock:
                    refs = self.__batch_references.pop_items(
                        self.__batch_size - len(objs),
                        uuid_lookup=self.__uuid_lookup,
                    )

                for req in self.__generate_stream_requests(objs, refs):
                    start, paused = time.time(), False
                    while (
                        self.__is_shutting_down.is_set()
                        or self.__is_shutdown.is_set()
                        or self.__is_oom.is_set()
                        or self.__is_hungup.is_set()
                    ):
                        if not paused:
                            logger.info("Server is shutting down, pausing batching loop...")
                            paused = True
                        time.sleep(refresh_time)
                        if time.time() - start > 300:
                            raise WeaviateBatchFailedToReestablishStreamError(
                                "Batch stream was not re-established within 5 minutes. Terminating batch."
                            )
                    if paused:
                        logger.info("Server is back up, resuming batching loop...")
                        paused = False
                    try:
                        self.__reqs.put(req, timeout=60)
                    except Full as e:
                        logger.warning(
                            "Batch queue is blocked for more than 60 seconds. Exiting the loop"
                        )
                        self.__bg_exception = e
                        return
            elif (
                self.__is_stopped.is_set()
                and not self.__sent_sentinel.is_set()
                and not self.__is_hungup.is_set()
                and not self.__is_shutdown.is_set()
                and not self.__is_shutting_down.is_set()
                and not self.__is_oom.is_set()
            ):
                self.__reqs.put(None)
                self.__sent_sentinel.set()
            time.sleep(refresh_time)

    def __generate_stream_requests(
        self,
        objects: List[BatchObject],
        references: List[BatchReference],
    ) -> Generator[batch_pb2.BatchStreamRequest, None, None]:
        per_object_overhead = 4  # extra overhead bytes per object in the request

        def request_maker():
            return batch_pb2.BatchStreamRequest()

        request = request_maker()
        total_size = request.ByteSize()

        inflight_objs = set()
        inflight_refs = set()
        for object_ in objects:
            obj = self.__batch_grpc.grpc_object(object_._to_internal())
            obj_size = obj.ByteSize() + per_object_overhead

            if total_size + obj_size >= self.__batch_grpc.grpc_max_msg_size:
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.objects.values.append(obj)
            total_size += obj_size
            inflight_objs.add(obj.uuid)

        for reference in references:
            ref = self.__batch_grpc.grpc_reference(reference._to_internal())
            ref_size = ref.ByteSize() + per_object_overhead

            if total_size + ref_size >= self.__batch_grpc.grpc_max_msg_size:
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.references.values.append(ref)
            total_size += ref_size
            inflight_refs.add(reference._to_beacon())

        with self.__acks_lock:
            self.__inflight_objs.update(inflight_objs)
            self.__inflight_refs.update(inflight_refs)

        if len(request.data.objects.values) > 0 or len(request.data.references.values) > 0:
            yield request

    def __send(
        self,
    ) -> Generator[batch_pb2.BatchStreamRequest, None, None]:
        self.__sent_sentinel.clear()
        yield batch_pb2.BatchStreamRequest(
            start=batch_pb2.BatchStreamRequest.Start(
                consistency_level=self.__batch_grpc._consistency_level,
            ),
        )
        stream_start = time.time()
        while self.__bg_exception is None:
            if self.__is_gcp_on_wcd:
                assert stream_start is not None, "stream_start should be set for GCP streams"
                if time.time() - stream_start > GCP_STREAM_TIMEOUT:
                    logger.info(
                        "GCP connections have a maximum lifetime. Re-establishing the batch stream to avoid timeout errors."
                    )
                    self.__is_renewing_stream.set()
                    yield batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop())
                    return
            try:
                req = self.__reqs.get(timeout=1)
                if req is None:
                    logger.info(
                        "Batching finished, stopping and closing the client-side of the stream"
                    )
                    yield batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop())
                    return
                yield req
                continue
            except Empty:
                if self.__is_shutting_down.is_set():
                    logger.info("Server shutting down, closing the client-side of the stream")
                    return
                elif self.__is_oom.is_set():
                    logger.info("Server out-of-memory, closing the client-side of the stream")
                    return
                elif self.__is_hungup.is_set():
                    logger.info("Detected hung up stream, closing the client-side of the stream")
                    return
                logger.info("Timed out getting request from queue, but not stopping, continuing...")
        logger.info("Batch send thread exiting due to exception...")

    def __recv(self) -> None:
        stream = self.__batch_grpc.stream(
            connection=self.__connection,
            requests=self.__send(),
        )
        self.__is_hungup.clear()
        self.__is_shutdown.clear()
        for message in stream:
            if message.HasField("started"):
                logger.info("Batch stream started successfully")

            if message.HasField("backoff"):
                if (
                    message.backoff.batch_size != self.__batch_size
                    and not self.__is_shutting_down.is_set()
                    and not self.__is_shutdown.is_set()
                    and not self.__is_oom.is_set()
                    and not self.__is_hungup.is_set()
                    and not self.__is_renewing_stream.is_set()
                    and not self.__is_stopped.is_set()
                ):
                    self.__batch_size = message.backoff.batch_size
                    logger.info(f"Updated batch size to {self.__batch_size} as per server request")

            if message.HasField("acks"):
                with self.__acks_lock:
                    self.__inflight_objs.difference_update(message.acks.uuids)
                    self.__inflight_refs.difference_update(message.acks.beacons)

            if message.HasField("results"):
                result_objs = BatchObjectReturn()
                result_refs = BatchReferenceReturn()
                failed_objs: List[ErrorObject] = []
                failed_refs: List[ErrorReference] = []
                for error in message.results.errors:
                    if error.HasField("uuid"):
                        try:
                            with self.__objs_cache_lock:
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
                        try:
                            with self.__refs_cache_lock:
                                cached = self.__refs_cache.pop(error.beacon)
                        except KeyError:
                            continue
                        err = ErrorReference(
                            message=error.error,
                            reference=cached,
                        )
                        failed_refs.append(err)
                        result_refs += BatchReferenceReturn(
                            errors={cached.index: err},
                        )
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
                            with self.__objs_cache_lock:
                                cached = self.__objs_cache.pop(success.uuid)
                            with self.__uuid_lookup_lock:
                                self.__uuid_lookup.discard(success.uuid)
                        except KeyError:
                            continue
                        uuid = uuid_package.UUID(success.uuid)
                        result_objs += BatchObjectReturn(
                            _all_responses=[uuid],
                            uuids={cached.index: uuid},
                        )
                    if success.HasField("beacon"):
                        try:
                            with self.__refs_cache_lock:
                                self.__refs_cache.pop(success.beacon, None)
                        except KeyError:
                            continue
                with self.__results_lock:
                    self.__results_for_wrapper.results.objs += result_objs
                    self.__results_for_wrapper.results.refs += result_refs
                    self.__results_for_wrapper.failed_objects.extend(failed_objs)
                    self.__results_for_wrapper.failed_references.extend(failed_refs)

            if message.HasField("out_of_memory"):
                logger.info(
                    "Server reported out-of-memory. Batching will wait at most 10 minutes for the server to scale-up. If the server does not recover within this time, the batch will terminate with an error."
                )
                self.__is_oom.set()
                with self.__objs_cache_lock:
                    self.__batch_objects.prepend(
                        [
                            o
                            for uuid in message.out_of_memory.uuids
                            if (o := self.__objs_cache.get(uuid)) is not None
                        ]
                    )
                with self.__refs_cache_lock:
                    self.__batch_references.prepend(
                        [
                            r
                            for beacon in message.out_of_memory.beacons
                            if (r := self.__refs_cache.get(beacon)) is not None
                        ]
                    )

            if message.HasField("shutting_down"):
                logger.info("Received shutting down message from server")
                self.__is_shutting_down.set()
                self.__is_oom.clear()

            if message.HasField("shutdown"):
                logger.info("Received shutdown finished message from server")
                self.__is_shutdown.set()
                self.__is_shutting_down.clear()

        # restart the stream if we were shutdown by the node we were connected to ensuring that the index is
        # propagated properly from it to the new one
        if self.__is_shutdown.is_set():
            self.__reconnect()
            logger.info("Restarting batch recv after shutdown...")
            return self.__recv()
        elif self.__is_renewing_stream.is_set():
            # restart the stream if we are renewing it (GCP connections have a max lifetime)
            logger.info("Restarting batch recv after renewing stream...")
            self.__is_renewing_stream.clear()
            return self.__recv()

        logger.info("Server closed the stream from its side, shutting down batch")
        self.__shutdown_loop.set()

    def __reconnect(self, retry: int = 0) -> None:
        if self.__consistency_level == ConsistencyLevel.ALL or self.__number_of_nodes == 1:
            # check that all nodes are available before reconnecting
            up_nodes = self.__cluster.get_nodes_status()
            while len(up_nodes) != self.__number_of_nodes or any(
                node["status"] != "HEALTHY" for node in up_nodes
            ):
                logger.info(
                    "Waiting for all nodes to be HEALTHY before reconnecting to batch stream..."
                )
                time.sleep(5)
                up_nodes = self.__cluster.get_nodes_status()
        try:
            logger.info(f"Trying to reconnect after shutdown... {retry + 1}/{5}")
            result(self.__connection.close("sync"))
            self.__connection.connect(force=True)
            logger.info("Reconnected successfully")
        except (WeaviateStartUpError, WeaviateGRPCUnavailableError) as e:
            if retry < 5:
                logger.warning(f"Failed to reconnect, after {retry} attempts. Retrying...")
                time.sleep(2**retry)
                self.__reconnect(retry + 1)
            else:
                logger.error("Failed to reconnect after 5 attempts")
                self.__bg_exception = e

    def __start_bg_threads(self):
        def loop_wrapper() -> None:
            try:
                self.__loop()
                logger.info("exited batch requests loop thread")
            except Exception as e:
                logger.error(e)
                self.__bg_exception = e

        def recv_wrapper() -> None:
            try:
                self.__recv()
                logger.info("exited batch receive thread")
            except Exception as e:
                if isinstance(e, WeaviateBatchStreamError) and (
                    "Socket closed" in e.message
                    or "context canceled" in e.message
                    or "Connection reset" in e.message
                    or "Received RST_STREAM with error code 2" in e.message
                ):
                    logger.error(f"Socket hang up detected in batch receive thread: {e.message}")
                    self.__is_hungup.set()
                else:
                    logger.error(e)
                    logger.error(type(e))
                    self.__bg_exception = e
            if self.__is_hungup.is_set():
                # this happens during ungraceful shutdown of the coordinator
                # lets restart the stream and add the cached objects again
                logger.warning("Stream closed unexpectedly, restarting...")
                self.__reconnect()
                with self.__objs_cache_lock:
                    self.__batch_objects.prepend(list(self.__objs_cache.values()))
                with self.__refs_cache_lock:
                    self.__batch_references.prepend(list(self.__refs_cache.values()))
                # start a new stream with a newly reconnected channel
                return recv_wrapper()

        self.__bg_threads = _BgThreads(
            loop=threading.Thread(
                target=loop_wrapper,
                daemon=True,
                name="BgBatchLoop",
            ),
            recv=threading.Thread(
                target=recv_wrapper,
                daemon=True,
                name="BgBatchRecv",
            ),
        )
        self.__bg_threads.start_recv()
        self.__bg_threads.start_loop()

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
        self.__batch_objects.add(batch_object)
        with self.__objs_cache_lock:
            self.__objs_cache[uuid] = batch_object
        self.__objs_count += 1

        while self.__is_blocked():
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
            self.__batch_references.add(batch_reference)
            with self.__refs_cache_lock:
                self.__refs_cache[batch_reference._to_beacon()] = batch_reference
                self.__refs_count += 1
            while self.__is_blocked():
                self.__check_bg_threads_alive()
                time.sleep(0.01)

    def __is_blocked(self):
        return (
            len(self.__inflight_objs) >= self.__batch_size
            or len(self.__inflight_refs) >= self.__batch_size * 2
            or self.__is_renewing_stream.is_set()
            or self.__is_shutting_down.is_set()
            or self.__is_shutdown.is_set()
            or self.__is_oom.is_set()
        )

    def __check_bg_threads_alive(self) -> None:
        if self.__all_threads_alive():
            return

        raise self.__bg_exception or Exception("Batch thread died unexpectedly")

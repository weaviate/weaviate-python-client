import threading
import time
import uuid as uuid_package
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from typing import Generator, List, Optional, Set, Union

from pydantic import ValidationError

from weaviate.collections.batch.base import (
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

        self.__bg_thread_exception: Optional[Exception] = None
        self.__is_oom = threading.Event()
        self.__is_shutting_down = threading.Event()
        self.__is_shutdown = threading.Event()

        self.__objs_cache_lock = threading.Lock()
        self.__refs_cache_lock = threading.Lock()
        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache: dict[str, BatchReference] = {}

        self.__acks_lock = threading.Lock()
        self.__inflight_objs: set[str] = set()
        self.__inflight_refs: set[str] = set()

        # maxsize=1 so that __send does not run faster than generator for __recv
        # thereby using too much buffer in case of server-side shutdown
        self.__reqs: Queue[Optional[batch_pb2.BatchStreamRequest]] = Queue(maxsize=1)

        self.__stop = False

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
        self.__bg_threads = [self.__start_bg_threads() for _ in range(1)]
        logger.warning(
            f"Provisioned {len(self.__bg_threads)} stream(s) to the server for batch processing"
        )
        now = time.time()
        while not self.__all_threads_alive():
            # wait for the stream to be started by __batch_stream
            time.sleep(0.01)
            if time.time() - now > 60:
                raise WeaviateBatchStreamError(
                    "Batch stream was not started within 60 seconds. Please check your connection."
                )

    def _shutdown(self) -> None:
        # Shutdown the current batch and wait for all requests to be finished
        self.flush()
        self.__stop = True

        # we are done, wait for bg threads to finish
        # self.__batch_stream will set the shutdown event when it receives
        # the stop message from the server
        while self.__any_threads_alive():
            time.sleep(0.05)
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

    def __send(self) -> None:
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
                    start = time.time()
                    while (
                        self.__is_oom.is_set()
                        or self.__is_shutting_down.is_set()
                        or self.__is_shutdown.is_set()
                    ):
                        # if we were shutdown by the node we were connected to, we need to wait for the stream to be restarted
                        # so that the connection is refreshed to a new node where the objects can be accepted
                        # otherwise, we wait until the stream has been started by __batch_stream to send the first batch
                        if not logged:
                            logger.warning("Waiting for stream to be re-established...")
                            logged = True
                            # put sentinel into our queue to signal the end of the current stream
                            self.__reqs.put(None)
                        time.sleep(1)
                        if time.time() - start > 300:
                            raise WeaviateBatchFailedToReestablishStreamError(
                                "Batch stream was not re-established within 5 minutes. Terminating batch."
                            )
                    if logged:
                        logger.warning("Stream re-established, resuming sending batches")
                    self.__reqs.put(req)
            elif self.__stop:
                # we are done, send the sentinel into our queue to be consumed by the batch sender
                self.__reqs.put(None)  # signal the end of the stream
                logger.warning("Batching finished, sent stop signal to batch stream")
                return
            time.sleep(refresh_time)

    def __beacon(self, ref: batch_pb2.BatchReference) -> str:
        return f"weaviate://localhost/{ref.from_collection}{f'#{ref.tenant}' if ref.tenant != '' else ''}/{ref.from_uuid}#{ref.name}->/{ref.to_collection}/{ref.to_uuid}"

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
            if self.__connection._weaviate_version.is_at_least(1, 35, 0):
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
            if self.__connection._weaviate_version.is_at_least(1, 35, 0):
                inflight_refs.add(reference._to_beacon())

        with self.__acks_lock:
            self.__inflight_objs.update(inflight_objs)
            self.__inflight_refs.update(inflight_refs)

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
            if self.__is_oom.is_set():
                logger.warning("Server out-of-memory, closing the client-side of the stream")
                return
            logger.warning("Received sentinel, but not stopping, continuing...")

    def __recv(self) -> None:
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
            if message.HasField("acks"):
                with self.__acks_lock:
                    self.__inflight_objs.difference_update(message.acks.uuids)
                    self.__uuid_lookup.difference_update(message.acks.uuids)
                    self.__inflight_refs.difference_update(message.acks.beacons)
            if message.HasField("results"):
                result_objs = BatchObjectReturn()
                result_refs = BatchReferenceReturn()
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
                        try:
                            cached = self.__refs_cache.pop(error.beacon)
                        except KeyError:
                            continue
                        err = ErrorReference(
                            message=error.error,
                            reference=error.beacon,  # pyright: ignore
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
                            cached = self.__objs_cache.pop(success.uuid)
                        except KeyError:
                            continue
                        uuid = uuid_package.UUID(success.uuid)
                        result_objs += BatchObjectReturn(
                            _all_responses=[uuid],
                            uuids={cached.index: uuid},
                        )
                    if success.HasField("beacon"):
                        try:
                            self.__refs_cache.pop(success.beacon, None)
                        except KeyError:
                            continue
                with self.__results_lock:
                    self.__results_for_wrapper.results.objs += result_objs
                    self.__results_for_wrapper.results.refs += result_refs
                    self.__results_for_wrapper.failed_objects.extend(failed_objs)
                    self.__results_for_wrapper.failed_references.extend(failed_refs)
            elif message.HasField("out_of_memory"):
                logger.warning(
                    "Server reported out-of-memory error. Batching will wait at most 10 minutes for the server to scale-up. If the server does not recover within this time, the batch will terminate with an error."
                )
                self.__is_oom.set()
                self.__batch_objects.prepend(
                    [self.__objs_cache[uuid] for uuid in message.out_of_memory.uuids]
                )
                self.__batch_references.prepend(
                    [self.__refs_cache[beacon] for beacon in message.out_of_memory.beacons]
                )
            elif message.HasField("shutting_down"):
                logger.warning(
                    "Received shutting down message from server, pausing sending until stream is re-established"
                )
                self.__is_shutting_down.set()
                self.__is_oom.clear()
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
            return self.__recv()
        else:
            logger.warning("Server closed the stream from its side, shutting down batch")
            return

    def __reconnect(self, retry: int = 0) -> None:
        if self.__consistency_level == ConsistencyLevel.ALL or self.__number_of_nodes == 1:
            # check that all nodes are available before reconnecting
            up_nodes = self.__cluster.get_nodes_status()
            while len(up_nodes) != self.__number_of_nodes or any(
                node["status"] != "HEALTHY" for node in up_nodes
            ):
                logger.warning(
                    "Waiting for all nodes to be HEALTHY before reconnecting to batch stream..."
                )
                time.sleep(5)
                up_nodes = self.__cluster.get_nodes_status()
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

        def send_wrapper() -> None:
            try:
                self.__send()
                logger.warning("exited batch send thread")
            except Exception as e:
                logger.error(e)
                self.__bg_thread_exception = e

        def recv_wrapper() -> None:
            socket_hung_up = False
            try:
                self.__recv()
                logger.warning("exited batch receive thread")
            except Exception as e:
                if isinstance(e, WeaviateBatchStreamError) and (
                    "Socket closed" in e.message
                    or "context canceled" in e.message
                    or "Connection reset" in e.message
                    or "Received RST_STREAM with error code 2" in e.message
                ):
                    logger.error(f"Socket hung up detected in batch receive thread: {e.message}")
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
                    self.__batch_objects.prepend(list(self.__objs_cache.values()))
                with self.__refs_cache_lock:
                    self.__batch_references.prepend(list(self.__refs_cache.values()))
                # start a new stream with a newly reconnected channel
                return recv_wrapper()

        threads = _BgThreads(
            send=threading.Thread(
                target=send_wrapper,
                daemon=True,
                name="BgBatchSend",
            ),
            recv=threading.Thread(
                target=recv_wrapper,
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
        self.__batch_objects.add(batch_object)
        with self.__objs_cache_lock:
            self.__objs_cache[uuid] = batch_object
        self.__objs_count += 1

        # block if queue gets too long or weaviate is overloaded - reading files is faster them sending them so we do
        # not need a long queue
        while len(self.__inflight_objs) >= self.__batch_size:
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
            while len(self.__inflight_refs) >= self.__batch_size * 2:
                self.__check_bg_threads_alive()
                time.sleep(0.01)

    def __check_bg_threads_alive(self) -> None:
        if self.__any_threads_alive():
            return

        raise self.__bg_thread_exception or Exception("Batch thread died unexpectedly")

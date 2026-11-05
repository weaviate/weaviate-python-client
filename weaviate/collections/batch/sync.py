import threading
import time
import uuid as uuid_package
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Full, Queue
from typing import Generator, List, Optional, Set, Union, cast

from grpc import Call, RpcError, StatusCode
from pydantic import ValidationError

from weaviate.collections.batch.base import (
    GCP_STREAM_TIMEOUT,
    ObjectsBatchRequest,
    ReferencesBatchRequest,
    _BatchDataWrapper,
    _BatchMode,
    _BatchStreamRequest,
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
    WeaviateClosedClientError,
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
        self.__consecutive_retries = 0
        self.__is_oom = threading.Event()
        self.__is_shutting_down = threading.Event()
        self.__is_hungup = threading.Event()
        self.__is_stopped = threading.Event()
        self.__oom_wait_time = 300

        self.__shutdown_loop = threading.Event()

        self.__objs_cache_lock = threading.Lock()
        self.__refs_cache_lock = threading.Lock()
        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache: dict[str, BatchReference] = {}

        self.__acks_lock = threading.Lock()
        self.__inflight_objs: set[str] = set()
        self.__inflight_refs: set[str] = set()
        self.__unresolved_objs: set[str] = set()
        self.__unresolved_refs: set[str] = set()

        # maxsize=1 so that __loop does not run faster than generator for __recv
        # thereby using too much buffer in case of server-side shutdown
        self.__reqs: Queue[Optional[_BatchStreamRequest]] = Queue(maxsize=1)
        self.__send_lock = threading.Lock()
        self.__replay_requests: deque[_BatchStreamRequest] = deque()
        self.__send_finished = False

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
        # this is how long an insert will take to timeout for, so we wait at most this time +5s for the batch to finish after shutdown is initiated, in case the server never hangs up
        shutdown_timeout = self.__connection.timeout_config.insert + 5
        try:
            self.__bg_threads.join(shutdown_timeout)
        except TimeoutError as e:
            raise WeaviateBatchStreamError(
                "Background batch threads did not terminate after forced shutdown."
            ) from e

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

    def __put(self, req: _BatchStreamRequest | None):
        while True:
            try:
                self.__reqs.put(req, timeout=1)
                return True
            except Full:
                if self.__bg_exception is not None or self.__shutdown_loop.is_set():
                    return False
                return self.__put(req)

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
                        len_o == len(self.__batch_objects) and len_r == len(self.__batch_references)
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
                        or self.__is_oom.is_set()
                        or self.__is_hungup.is_set()
                    ):
                        if not paused:
                            logger.info("Server is shutting down, pausing batching loop...")
                            paused = True
                        time.sleep(refresh_time)
                        if self.__bg_exception is not None:
                            return
                        if time.time() - start > self.__oom_wait_time:
                            raise WeaviateBatchFailedToReestablishStreamError(
                                f"Batch stream was not re-established within {self.__oom_wait_time} seconds after an OOM message. Terminating batch."
                            )
                    if paused:
                        logger.info("Server is back up, resuming batching loop...")
                        paused = False
                    if not self.__put(req):
                        logger.info("Batch loop is shutting down, stopping putting requests...")
                        return
            elif (
                self.__is_stopped.is_set()
                and not self.__is_hungup.is_set()
                and not self.__is_shutting_down.is_set()
                and not self.__is_oom.is_set()
            ):
                self.__put(None)
                logger.info("Sent sentinel, stopping batch loop...")
                return
            time.sleep(refresh_time)

    def __generate_stream_requests(
        self,
        objects: List[BatchObject],
        references: List[BatchReference],
    ) -> Generator[_BatchStreamRequest, None, None]:
        per_object_overhead = 4  # extra overhead bytes per object in the request

        def request_maker():
            return batch_pb2.BatchStreamRequest()

        request = request_maker()
        total_size = request.ByteSize()

        uuids, beacons = set(), set()
        for object_ in objects:
            obj = self.__batch_grpc.grpc_object(object_._to_internal())
            obj_size = obj.ByteSize() + per_object_overhead

            if obj_size > self.__batch_grpc.grpc_max_msg_size:
                raise WeaviateBatchValidationError(
                    f"Object with uuid {object_.uuid} is too large to be sent in a batch request. Size: {obj_size} bytes, max size: {self.__batch_grpc.grpc_max_msg_size} bytes."
                )

            if total_size + obj_size >= self.__batch_grpc.grpc_max_msg_size:
                yield _BatchStreamRequest(request, uuids, beacons)
                request = request_maker()
                total_size = request.ByteSize()
                uuids, beacons = set(), set()

            request.data.objects.values.append(obj)
            total_size += obj_size
            uuids.add(obj.uuid)

        for reference in references:
            ref = self.__batch_grpc.grpc_reference(reference.model_copy()._to_internal())
            ref_size = ref.ByteSize() + per_object_overhead

            if total_size + ref_size >= self.__batch_grpc.grpc_max_msg_size:
                yield _BatchStreamRequest(request, uuids, beacons)
                request = request_maker()
                total_size = request.ByteSize()
                uuids, beacons = set(), set()

            request.data.references.values.append(ref)
            total_size += ref_size
            beacons.add(reference._to_beacon())

        if len(request.data.objects.values) > 0 or len(request.data.references.values) > 0:
            yield _BatchStreamRequest(request, uuids, beacons)

    def __send(
        self,
        stopped: threading.Event,
    ) -> Generator[batch_pb2.BatchStreamRequest, None, None]:
        yield batch_pb2.BatchStreamRequest(
            start=batch_pb2.BatchStreamRequest.Start(
                consistency_level=self.__batch_grpc._consistency_level,
            ),
        )
        stream_start = time.time()
        while self.__bg_exception is None and not stopped.is_set():
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
                with self.__send_lock:
                    if stopped.is_set():
                        return
                    if self.__replay_requests:
                        req = self.__replay_requests.popleft()
                    elif self.__send_finished:
                        req = None
                    else:
                        req = self.__reqs.get(timeout=0.1)
                    if req is not None:
                        with self.__acks_lock:
                            self.__inflight_objs.update(req.uuids)
                            self.__inflight_refs.update(req.beacons)
                            self.__unresolved_objs.update(req.uuids)
                            self.__unresolved_refs.update(req.beacons)
                if req is None:
                    self.__send_finished = True
                    logger.info(
                        "Batching finished, stopping and closing the client-side of the stream"
                    )
                    yield batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop())
                    return
                yield req.proto
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
                logger.debug(
                    "Timed out getting request from queue, but not stopping, continuing..."
                )
        logger.info("Batch send thread exiting due to exception...")

    def __stream(self) -> Generator[batch_pb2.BatchStreamReply, None, None]:
        stopped = threading.Event()
        try:
            yield from self.__batch_grpc.stream(
                connection=self.__connection,
                requests=self.__send(stopped),
            )
        finally:
            # gRPC may still be waiting in next(requests) after the RPC ends.
            # Stop that iterator before it can take requests for its replacement.
            stopped.set()
            with self.__send_lock:
                pass  # Wait for any queue read already in progress before replaying.

    def __recv(self) -> bool:
        self.__is_renewing_stream.clear()
        self.__is_shutting_down.clear()
        self.__is_hungup.clear()
        for message in self.__stream():
            if message.HasField("started"):
                logger.info("Batch stream started successfully")

            if message.HasField("backoff"):
                if (
                    message.backoff.batch_size != self.__batch_size
                    and not self.__is_shutting_down.is_set()
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
                with self.__acks_lock:
                    for entry in [*message.results.errors, *message.results.successes]:
                        if entry.HasField("uuid"):
                            self.__unresolved_objs.discard(entry.uuid)
                        if entry.HasField("beacon"):
                            self.__unresolved_refs.discard(entry.beacon)
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
                if message.results.errors or message.results.successes:
                    self.__consecutive_retries = 0

            if message.HasField("out_of_memory"):
                logger.info(
                    "Server reported out-of-memory. Batching will wait at most 10 minutes for the server to scale-up. If the server does not recover within this time, the batch will terminate with an error."
                )
                self.__is_oom.set()
                self.__oom_wait_time = message.out_of_memory.wait_time
                with self.__acks_lock:
                    self.__unresolved_objs.difference_update(message.out_of_memory.uuids)
                    self.__unresolved_refs.difference_update(message.out_of_memory.beacons)
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

        # restart the stream if we were shutdown by the node we were connected to ensuring that the index is
        # propagated properly from it to the new one
        if self.__is_shutting_down.is_set():
            self.__reconnect()
            logger.info("Restarting batch recv after shutdown...")
            return True
        elif self.__is_renewing_stream.is_set():
            # restart the stream if we are renewing it (GCP connections have a max lifetime)
            logger.info("Restarting batch recv after renewing stream...")
            return True

        logger.info("Server closed the stream from its side, shutting down batch")
        self.__shutdown_loop.set()
        return False

    def __wait_for_reconnect(self, delay: float) -> None:
        deadline = time.monotonic() + delay
        while True:
            if not self.__connection.is_connected():
                raise WeaviateClosedClientError()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 0.1))

    def __wait_for_channel(self) -> None:
        self.__wait_for_reconnect(0)
        if self.__consistency_level == ConsistencyLevel.ALL or self.__number_of_nodes == 1:
            # check that all nodes are available before reconnecting
            deadline = time.monotonic() + self.__oom_wait_time
            up_nodes = self.__cluster.get_nodes_status()
            while len(up_nodes) != self.__number_of_nodes or any(
                node["status"] != "HEALTHY" for node in up_nodes
            ):
                logger.info(
                    "Waiting for all nodes to be HEALTHY before reconnecting to batch stream..."
                )
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WeaviateBatchFailedToReestablishStreamError(
                        "Batch stream was not re-established because cluster nodes did not become HEALTHY."
                    )
                self.__wait_for_reconnect(min(5, remaining))
                up_nodes = self.__cluster.get_nodes_status()
        # gRPC reconnects the existing channel. Closing the client here would
        # cancel every other stream and query sharing that connection.
        if self.__connection._skip_init_checks:
            return
        for retry in range(6):
            self.__wait_for_reconnect(0)
            try:
                result(self.__connection._ping_grpc("sync"))
                return
            except WeaviateGRPCUnavailableError:
                if retry == 5:
                    raise
                self.__wait_for_reconnect(2**retry)

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
            while True:
                try:
                    if self.__recv():
                        continue
                    logger.info("exited batch receive thread")
                    return
                except Exception as e:
                    if (
                        not isinstance(e, WeaviateBatchStreamError)
                        or not (
                            isinstance(e.__cause__, RpcError)
                            and cast(Call, e.__cause__).code() == StatusCode.UNAVAILABLE
                            or "Socket closed" in e.message
                            or "context canceled" in e.message
                            or "Connection reset" in e.message
                            or "Received RST_STREAM with error code 2" in e.message
                        )
                        or self.__consecutive_retries >= 5
                    ):
                        logger.error(e)
                        self.__bg_exception = e
                        return
                    self.__is_hungup.set()
                    try:
                        if self.__consecutive_retries:
                            self.__wait_for_reconnect(2 ** (self.__consecutive_retries - 1))
                        self.__consecutive_retries += 1
                        self.__wait_for_channel()
                    except Exception as reconnect_error:
                        self.__bg_exception = reconnect_error
                        return
                    # Replay only requests taken by this RPC, not objects still
                    # waiting in the producer's queues. The producer may already
                    # have stopped, so send these directly on the replacement RPC.
                    with self.__objs_cache_lock:
                        objects = [
                            obj
                            for uuid in self.__unresolved_objs
                            if (obj := self.__objs_cache.get(uuid)) is not None
                        ]
                    with self.__refs_cache_lock:
                        references = [
                            ref
                            for beacon in self.__unresolved_refs
                            if (ref := self.__refs_cache.get(beacon)) is not None
                        ]
                    self.__replay_requests.extendleft(
                        reversed(list(self.__generate_stream_requests(objects, references)))
                    )
                    with self.__acks_lock:
                        self.__inflight_objs.clear()
                        self.__inflight_refs.clear()
                        self.__unresolved_objs.clear()
                        self.__unresolved_refs.clear()

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
                logger.warning("Batch is blocked, waiting to add more references...")
                self.__check_bg_threads_alive()
                time.sleep(0.01)

    def __is_blocked(self):
        return (
            len(self.__inflight_objs) >= self.__batch_size
            or len(self.__inflight_refs) >= self.__batch_size * 2
            or self.__is_renewing_stream.is_set()
            or self.__is_shutting_down.is_set()
            or self.__is_oom.is_set()
        )

    def __check_bg_threads_alive(self) -> None:
        if self.__all_threads_alive():
            return

        raise self.__bg_exception or Exception("Batch thread died unexpectedly")

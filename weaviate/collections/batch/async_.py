import asyncio
import time
import uuid as uuid_package
from typing import (
    AsyncGenerator,
    Generator,
    List,
    Optional,
    Set,
    Union,
)

from pydantic import ValidationError

from weaviate.collections.batch.base import (
    GCP_STREAM_TIMEOUT,
    ObjectsBatchRequest,
    ReferencesBatchRequest,
    _BatchDataWrapper,
    _ClusterBatchAsync,
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
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync
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


class _BgTasks:
    def __init__(self, recv: asyncio.Task[None], loop: asyncio.Task[None]) -> None:
        self.recv = recv
        self.loop = loop
        self.send_started = False

    def all_alive(self) -> bool:
        return all([not self.recv.done(), not self.loop.done()])

    async def gather(self) -> None:
        tasks = [self.recv, self.loop]
        await asyncio.gather(*tasks)


class _BatchBaseAsync:
    def __init__(
        self,
        connection: ConnectionAsync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        objects: Optional[ObjectsBatchRequest[BatchObject]] = None,
        references: Optional[ReferencesBatchRequest[BatchReference]] = None,
    ) -> None:
        self.__batch_objects = objects or ObjectsBatchRequest[BatchObject]()
        self.__batch_references = references or ReferencesBatchRequest[BatchReference]()

        self.__connection = connection
        self.__is_gcp_on_wcd = connection._connection_params.is_gcp_on_wcd()
        self.__is_renewing_stream = asyncio.Event()
        self.__consistency_level: ConsistencyLevel = consistency_level or ConsistencyLevel.QUORUM
        self.__batch_size = 100

        self.__batch_grpc = _BatchGRPC(
            connection._weaviate_version, self.__consistency_level, connection._grpc_max_msg_size
        )
        self.__cluster = _ClusterBatchAsync(self.__connection)

        # lookup table for objects that are currently being processed - is used to not send references from objects that have not been added yet
        self.__uuid_lookup_lock = asyncio.Lock()
        self.__uuid_lookup: Set[str] = set()

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__objs_count = 0
        self.__refs_count = 0

        self.__is_oom = asyncio.Event()
        self.__is_shutting_down = asyncio.Event()
        self.__is_shutdown = asyncio.Event()

        self.__objs_cache_lock = asyncio.Lock()
        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache_lock = asyncio.Lock()
        self.__refs_cache: dict[str, BatchReference] = {}

        self.__inflight_objs: set[str] = set()
        self.__inflight_refs: set[str] = set()

        # maxsize=1 so that __send does not run faster than generator for __recv
        # thereby using too much buffer in case of server-side shutdown
        self.__reqs: asyncio.Queue[Optional[batch_pb2.BatchStreamRequest]] = asyncio.Queue(
            maxsize=1
        )

        self.__stop = False
        self.__bg_exception: Optional[Exception] = None
        self.__bg_tasks: Optional[_BgTasks] = None

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

    def __all_tasks_alive(self) -> bool:
        return self.__bg_tasks is not None and self.__bg_tasks.all_alive()

    async def _start(self):
        self.__number_of_nodes = await self.__cluster.get_number_of_nodes()

        async def loop_wrapper() -> None:
            try:
                await self.__loop()
                logger.info("exited batch loop task")
            except Exception as e:
                logger.error(e)
                self.__bg_exception = e

        async def recv_wrapper() -> None:
            socket_hung_up = False
            try:
                await self.__recv()
                logger.info("exited batch recv task")
            except Exception as e:
                if isinstance(e, WeaviateBatchStreamError) and (
                    "Socket closed" in e.message or "context canceled" in e.message
                ):
                    logger.warning(e)
                    socket_hung_up = True
                else:
                    logger.error(e)
                    self.__bg_exception = e
            if socket_hung_up:
                # this happens during ungraceful shutdown of the coordinator
                # lets restart the stream and add the cached objects again
                logger.warning("Stream closed unexpectedly, restarting...")
                await self.__reconnect()
                # server sets this whenever it restarts, gracefully or unexpectedly, so need to clear it now
                self.__is_shutting_down.clear()
                async with self.__objs_cache_lock:
                    await self.__batch_objects.aprepend(list(self.__objs_cache.values()))
                async with self.__refs_cache_lock:
                    await self.__batch_references.aprepend(list(self.__refs_cache.values()))
                # start a new stream with a newly reconnected channel
                return await recv_wrapper()

        recv = asyncio.create_task(recv_wrapper())
        loop = asyncio.create_task(loop_wrapper())

        self.__bg_tasks = _BgTasks(
            recv=recv,
            loop=loop,
        )

    async def _wait(self):
        assert self.__bg_tasks is not None
        await self.__bg_tasks.gather()

        # copy the results to the public results
        self.__results_for_wrapper_backup.results = self.__results_for_wrapper.results
        self.__results_for_wrapper_backup.failed_objects = self.__results_for_wrapper.failed_objects
        self.__results_for_wrapper_backup.failed_references = (
            self.__results_for_wrapper.failed_references
        )
        self.__results_for_wrapper_backup.imported_shards = (
            self.__results_for_wrapper.imported_shards
        )

    async def _shutdown(self) -> None:
        self.__stop = True

    async def __loop(self) -> None:
        refresh_time: float = 0.01
        while self.__bg_exception is None:
            if len(self.__batch_objects) + len(self.__batch_references) > 0:
                start = time.time()
                while (len_o := len(self.__batch_objects)) + (
                    len_r := len(self.__batch_references)
                ) < self.__batch_size:
                    # wait for more objects to be added up to the batch size
                    await asyncio.sleep(refresh_time)
                    if time.time() - start >= 1 and (
                        len_o == len(self.__batch_objects) or len_r == len(self.__batch_references)
                    ):
                        # no new objects were added in the last second, exit the loop
                        break

                objs = self.__batch_objects.pop_items(self.__batch_size)
                async with self.__uuid_lookup_lock:
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
                    ):
                        if not paused:
                            logger.info("Server is shutting down, pausing batching loop...")
                            await self.__reqs.put(None)
                            paused = True
                        await asyncio.sleep(1)
                        if time.time() - start > 300:
                            raise WeaviateBatchFailedToReestablishStreamError(
                                "Batch stream was not re-established within 5 minutes. Terminating batch."
                            )
                    try:
                        await asyncio.wait_for(self.__reqs.put(req), timeout=60)
                    except asyncio.TimeoutError as e:
                        logger.warning(
                            "Batch queue is blocked for more than 60 seconds. Exiting the loop"
                        )
                        self.__bg_exception = e
                        return
            elif self.__stop:
                # we are done, send the sentinel into our queue to be consumed by the batch sender
                await self.__reqs.put(None)  # signal the end of the stream
                logger.info("Batching finished, sent stop signal to batch stream")
                return
            await asyncio.sleep(refresh_time)

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
                self.__inflight_objs.update(inflight_objs)
                self.__inflight_refs.update(inflight_refs)
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
                self.__inflight_objs.update(inflight_objs)
                self.__inflight_refs.update(inflight_refs)
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.references.values.append(ref)
            total_size += ref_size
            inflight_refs.add(reference._to_beacon())

        if len(request.data.objects.values) > 0 or len(request.data.references.values) > 0:
            self.__inflight_objs.update(inflight_objs)
            self.__inflight_refs.update(inflight_refs)
            yield request

    async def __send(
        self,
    ) -> AsyncGenerator[batch_pb2.BatchStreamRequest, None]:
        yield batch_pb2.BatchStreamRequest(
            start=batch_pb2.BatchStreamRequest.Start(
                consistency_level=self.__batch_grpc._consistency_level,
            ),
        )
        stream_start = time.time()
        while self.__bg_exception is None:
            if self.__is_gcp_on_wcd:
                assert stream_start is not None
                if time.time() - stream_start > GCP_STREAM_TIMEOUT:
                    logger.info(
                        "GCP connections have a maximum lifetime. Re-establishing the batch stream to avoid timeout errors."
                    )
                    self.__is_renewing_stream.set()
                    yield batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop())
                    return
            try:
                req = await asyncio.wait_for(self.__reqs.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            if req is not None:
                yield req
                continue
            if self.__stop and not (
                self.__is_shutting_down.is_set() or self.__is_shutdown.is_set()
            ):
                logger.info("Batching finished, closing the client-side of the stream")
                yield batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop())
                return
            if self.__is_shutting_down.is_set():
                logger.info("Server shutting down, closing the client-side of the stream")
                return
            if self.__is_oom.is_set():
                logger.info("Server out-of-memory, closing the client-side of the stream")
                return
            logger.info("Received sentinel, but not stopping, continuing...")
        logger.info("Batch send thread exiting due to exception...")

    async def __recv(self) -> None:
        stream = self.__batch_grpc.astream(
            connection=self.__connection,
            requests=self.__send(),
        )
        self.__is_shutdown.clear()
        async for message in stream:
            if message.HasField("started"):
                logger.info("Batch stream started successfully")

            if message.HasField("backoff"):
                if (
                    message.backoff.batch_size != self.__batch_size
                    and not self.__is_shutting_down.is_set()
                    and not self.__is_shutdown.is_set()
                    and not self.__is_oom.is_set()
                    and not self.__stop
                ):
                    self.__batch_size = message.backoff.batch_size
                    logger.info(f"Updated batch size to {self.__batch_size} as per server request")

            if message.HasField("acks"):
                self.__inflight_objs.difference_update(message.acks.uuids)
                async with self.__uuid_lookup_lock:
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
                            async with self.__objs_cache_lock:
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
                            async with self.__refs_cache_lock:
                                cached = self.__refs_cache.pop(error.beacon)
                        except KeyError:
                            continue
                        err = ErrorReference(
                            message=error.error,
                            reference=cached,
                        )
                        result_refs += BatchReferenceReturn(
                            errors={cached.index: err},
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
                            async with self.__objs_cache_lock:
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
                            async with self.__refs_cache_lock:
                                self.__refs_cache.pop(success.beacon)
                        except KeyError:
                            continue
                self.__results_for_wrapper.results.objs += result_objs
                self.__results_for_wrapper.results.refs += result_refs
                self.__results_for_wrapper.failed_objects.extend(failed_objs)
                self.__results_for_wrapper.failed_references.extend(failed_refs)

            if message.HasField("out_of_memory"):
                logger.info(
                    "Server reported out-of-memory. Batching will wait at most 10 minutes for the server to scale-up. If the server does not recover within this time, the batch will terminate with an error."
                )
                self.__is_oom.set()
                await self.__batch_objects.aprepend(
                    [self.__objs_cache[uuid] for uuid in message.out_of_memory.uuids]
                )
                await self.__batch_references.aprepend(
                    [self.__refs_cache[beacon] for beacon in message.out_of_memory.beacons]
                )

            if message.HasField("shutting_down"):
                logger.info("Received shutting down message from server")
                self.__is_shutting_down.set()
                self.__is_oom.clear()

            if message.HasField("shutdown"):
                logger.info("Received shutdown finished message from server")
                self.__is_shutdown.set()
                self.__is_shutting_down.clear()

        if self.__is_shutdown.is_set():
            await self.__reconnect()
            logger.info("Restarting batch recv after shutdown...")
            return await self.__recv()

        elif self.__is_renewing_stream.is_set():
            # restart the stream if we are renewing it (GCP connections have a max lifetime)
            logger.info("Restarting batch recv after renewing stream...")
            self.__is_renewing_stream.clear()
            return await self.__recv()

        logger.info("Server closed the stream from its side, shutting down batch")

    async def __reconnect(self, retry: int = 0) -> None:
        if self.__consistency_level == ConsistencyLevel.ALL or self.__number_of_nodes == 1:
            # check that all nodes are available before reconnecting
            up_nodes = await self.__cluster.get_nodes_status()
            while len(up_nodes) != self.__number_of_nodes or any(
                node["status"] != "HEALTHY" for node in up_nodes
            ):
                logger.info(
                    "Waiting for all nodes to be HEALTHY before reconnecting to batch stream..."
                )
                await asyncio.sleep(5)
                up_nodes = await self.__cluster.get_nodes_status()
        try:
            logger.info(f"Trying to reconnect after shutdown... {retry + 1}/{5}")
            await aresult(self.__connection.close("async"))
            await self.__connection.connect(force=True)
            logger.info("Reconnected successfully")
        except (WeaviateStartUpError, WeaviateGRPCUnavailableError) as e:
            if retry < 5:
                logger.warning(f"Failed to reconnect, after {retry} attempts. Retrying...")
                await asyncio.sleep(2**retry)
                await self.__reconnect(retry + 1)
            else:
                logger.error("Failed to reconnect after 5 attempts following server shutdown")
                self.__bg_exception = e

    async def flush(self) -> None:
        """Flush the batch queue and wait for all requests to be finished."""
        # bg thread is sending objs+refs automatically, so simply wait for everything to be done
        while len(self.__batch_objects) > 0 or len(self.__batch_references) > 0:
            await asyncio.sleep(0.01)

    async def _add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[str] = None,
    ) -> UUID:
        self.__check_bg_tasks_alive()
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
        async with self.__uuid_lookup_lock:
            self.__uuid_lookup.add(uuid)
        await self.__batch_objects.aadd(batch_object)
        async with self.__objs_cache_lock:
            self.__objs_cache[uuid] = batch_object
            self.__objs_count += 1

        while self.__is_blocked():
            self.__check_bg_tasks_alive()
            await asyncio.sleep(0.01)

        assert batch_object.uuid is not None
        await asyncio.sleep(0)
        return batch_object.uuid

    async def _add_reference(
        self,
        from_object_uuid: UUID,
        from_object_collection: str,
        from_property_name: str,
        to: ReferenceInput,
        tenant: Optional[str] = None,
    ) -> None:
        self.__check_bg_tasks_alive()
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
            await self.__batch_references.aadd(batch_reference)
            async with self.__refs_cache_lock:
                self.__refs_cache[batch_reference._to_beacon()] = batch_reference
                self.__refs_count += 1
            while self.__is_blocked():
                self.__check_bg_tasks_alive()
                await asyncio.sleep(0.01)

    def __is_blocked(self):
        return (
            len(self.__inflight_objs) >= self.__batch_size
            or len(self.__inflight_refs) >= self.__batch_size * 2
            or self.__is_renewing_stream.is_set()
            or self.__is_shutting_down.is_set()
            or self.__is_shutdown.is_set()
            or self.__is_oom.is_set()
        )

    def __check_bg_tasks_alive(self) -> None:
        if self.__all_tasks_alive():
            return

        raise self.__bg_exception or Exception("Batch tasks died unexpectedly")

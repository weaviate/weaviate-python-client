import asyncio
import time
import uuid as uuid_package
from typing import (
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
from weaviate.connect.v4 import ConnectionAsync
from weaviate.exceptions import (
    WeaviateBatchStreamError,
    WeaviateBatchValidationError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
)
from weaviate.logger import logger
from weaviate.proto.v1 import batch_pb2
from weaviate.types import UUID, VECTORS


class _BgTasks:
    def __init__(
        self, send: asyncio.Task[None], recv: asyncio.Task[None], loop: asyncio.Task[None]
    ) -> None:
        self.send = send
        self.recv = recv
        self.loop = loop


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
        self.__stream_start: Optional[float] = None
        self.__is_renewing_stream = asyncio.Event()
        self.__consistency_level: ConsistencyLevel = consistency_level or ConsistencyLevel.QUORUM
        self.__batch_size = 100

        self.__batch_grpc = _BatchGRPC(
            connection._weaviate_version, self.__consistency_level, connection._grpc_max_msg_size
        )
        self.__stream = self.__connection.grpc_batch_stream()

        # lookup table for objects that are currently being processed - is used to not send references from objects that have not been added yet
        self.__uuid_lookup: Set[str] = set()

        # we do not want that users can access the results directly as they are not thread-safe
        self.__results_for_wrapper_backup = results
        self.__results_for_wrapper = _BatchDataWrapper()

        self.__objs_count = 0
        self.__refs_count = 0

        self.__is_oom = asyncio.Event()
        self.__is_shutting_down = asyncio.Event()
        self.__is_shutdown = asyncio.Event()

        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache: dict[str, BatchReference] = {}

        self.__inflight_objs: set[str] = set()
        self.__inflight_refs: set[str] = set()

        # maxsize=1 so that __send does not run faster than generator for __recv
        # thereby using too much buffer in case of server-side shutdown
        self.__reqs: asyncio.Queue[Optional[batch_pb2.BatchStreamRequest]] = asyncio.Queue(
            maxsize=1
        )

        self.__stop = False
        self.__shutdown_send_task = asyncio.Event()

    @property
    def number_errors(self) -> int:
        """Return the number of errors in the batch."""
        return len(self.__results_for_wrapper.failed_objects) + len(
            self.__results_for_wrapper.failed_references
        )

    async def _start(self):
        async def send_wrapper() -> None:
            try:
                await self.__send()
                logger.warning("exited batch send thread")
            except Exception as e:
                logger.error(e)
                self.__bg_thread_exception = e

        async def loop_wrapper() -> None:
            try:
                await self.__loop()
                logger.warning("exited batch loop thread")
            except Exception as e:
                logger.error(e)
                self.__bg_thread_exception = e

        async def recv_wrapper() -> None:
            socket_hung_up = False
            try:
                await self.__recv()
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
                await self.__reconnect()
                # server sets this whenever it restarts, gracefully or unexpectedly, so need to clear it now
                self.__is_shutting_down.clear()
                await self.__batch_objects.aprepend(list(self.__objs_cache.values()))
                await self.__batch_references.aprepend(list(self.__refs_cache.values()))
                # start a new stream with a newly reconnected channel
                return await recv_wrapper()

        return _BgTasks(
            send=asyncio.create_task(send_wrapper()),
            recv=asyncio.create_task(recv_wrapper()),
            loop=asyncio.create_task(loop_wrapper()),
        )

    async def _shutdown(self) -> None:
        # Shutdown the current batch and wait for all requests to be finished
        await self.flush()
        self.__stop = True

        # copy the results to the public results
        self.__results_for_wrapper_backup.results = self.__results_for_wrapper.results
        self.__results_for_wrapper_backup.failed_objects = self.__results_for_wrapper.failed_objects
        self.__results_for_wrapper_backup.failed_references = (
            self.__results_for_wrapper.failed_references
        )
        self.__results_for_wrapper_backup.imported_shards = (
            self.__results_for_wrapper.imported_shards
        )

    async def __loop(self) -> None:
        refresh_time: float = 0.01
        while True:
            if len(self.__batch_objects) + len(self.__batch_references) > 0:
                self._batch_send = True
                start = time.time()
                while (len_o := len(self.__batch_objects)) + (
                    len_r := len(self.__batch_references)
                ) < self.__batch_size:
                    # wait for more objects to be added up to the batch size
                    await asyncio.sleep(0.01)
                    if self.__shutdown_send_task.is_set():
                        logger.warning("Tasks were shutdown, exiting batch send loop")
                        # shutdown was requested, exit early
                        await self.__reqs.put(None)
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

                for req in self.__generate_stream_requests(objs, refs):
                    await self.__reqs.put(req)
            elif self.__stop:
                # we are done, send the sentinel into our queue to be consumed by the batch sender
                await self.__reqs.put(None)  # signal the end of the stream
                logger.warning("Batching finished, sent stop signal to batch stream")
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

        self.__inflight_objs.update(inflight_objs)
        self.__inflight_refs.update(inflight_refs)

        if len(request.data.objects.values) > 0 or len(request.data.references.values) > 0:
            yield request

    async def __send(self):
        await self.__connection.grpc_batch_stream_write(
            stream=self.__stream,
            request=batch_pb2.BatchStreamRequest(
                start=batch_pb2.BatchStreamRequest.Start(
                    consistency_level=self.__batch_grpc._consistency_level,
                ),
            ),
        )
        while True:
            if self.__is_gcp_on_wcd:
                assert self.__stream_start is not None
                if time.time() - self.__stream_start > GCP_STREAM_TIMEOUT:
                    logger.warning(
                        "GCP connections have a maximum lifetime. Re-establishing the batch stream to avoid timeout errors."
                    )
                    await self.__connection.grpc_batch_stream_write(
                        self.__stream,
                        batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop()),
                    )
                    self.__is_renewing_stream.set()
                    return
            req = await self.__reqs.get()
            if req is not None:
                await self.__connection.grpc_batch_stream_write(self.__stream, req)
                continue
            if self.__stop and not (
                self.__is_shutting_down.is_set() or self.__is_shutdown.is_set()
            ):
                logger.warning("Batching finished, closing the client-side of the stream")
                await self.__connection.grpc_batch_stream_write(
                    self.__stream,
                    batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop()),
                )
                return
            if self.__is_shutting_down.is_set():
                logger.warning("Server shutting down, closing the client-side of the stream")
                return
            if self.__is_oom.is_set():
                logger.warning("Server out-of-memory, closing the client-side of the stream")
                return
            logger.warning("Received sentinel, but not stopping, continuing...")

    async def __recv(self) -> None:
        while True:
            message = await self.__connection.grpc_batch_stream_read(self.__stream)
            if not isinstance(message, batch_pb2.BatchStreamReply):
                logger.warning("Server closed the stream from its side, shutting down batch")
                return
            if message.HasField("started"):
                logger.warning("Batch stream started successfully")
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
                self.__results_for_wrapper.results.objs += result_objs
                self.__results_for_wrapper.results.refs += result_refs
                self.__results_for_wrapper.failed_objects.extend(failed_objs)
                self.__results_for_wrapper.failed_references.extend(failed_refs)
            if message.HasField("out_of_memory"):
                logger.warning(
                    "Server reported out-of-memory error. Batching will wait at most 10 minutes for the server to scale-up. If the server does not recover within this time, the batch will terminate with an error."
                )
                self.__is_oom.set()
                await self.__batch_objects.aprepend(
                    [self.__objs_cache[uuid] for uuid in message.out_of_memory.uuids]
                )
                await self.__batch_references.aprepend(
                    [self.__refs_cache[beacon] for beacon in message.out_of_memory.beacons]
                )
            if message.HasField("shutting_down"):
                logger.warning(
                    "Received shutting down message from server, pausing sending until stream is re-established"
                )
                self.__is_shutting_down.set()
            if message.HasField("shutdown"):
                logger.warning("Received shutdown finished message from server")
                self.__is_shutdown.set()
                self.__is_shutting_down.clear()
                await self.__reconnect()

            # restart the stream if we were shutdown by the node we were connected to
            if self.__is_shutdown.is_set():
                logger.warning("Restarting batch recv after shutdown...")
                self.__is_shutdown.clear()
                return await self.__recv()

    async def __reconnect(self, retry: int = 0) -> None:
        try:
            logger.warning(f"Trying to reconnect after shutdown... {retry + 1}/{5}")
            self.__connection.close("sync")
            await self.__connection.connect(force=True)
            logger.warning("Reconnected successfully")
            self.__stream = self.__connection.grpc_batch_stream()
        except (WeaviateStartUpError, WeaviateGRPCUnavailableError) as e:
            if retry < 5:
                await asyncio.sleep(2**retry)
                await self.__reconnect(retry + 1)
            else:
                logger.error("Failed to reconnect after 5 attempts")
                self.__bg_thread_exception = e

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
        self.__uuid_lookup.add(uuid)
        await self.__batch_objects.aadd(batch_object)
        self.__objs_cache[uuid] = batch_object
        self.__objs_count += 1

        while len(self.__inflight_objs) >= self.__batch_size:
            await asyncio.sleep(0.01)

        assert batch_object.uuid is not None
        return batch_object.uuid

    async def _add_reference(
        self,
        from_object_uuid: UUID,
        from_object_collection: str,
        from_property_name: str,
        to: ReferenceInput,
        tenant: Optional[str] = None,
    ) -> None:
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
            self.__refs_cache[batch_reference._to_beacon()] = batch_reference
            self.__refs_count += 1
            while len(self.__inflight_refs) >= self.__batch_size * 2:
                await asyncio.sleep(0.01)

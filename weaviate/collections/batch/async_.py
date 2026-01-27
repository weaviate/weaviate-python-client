import asyncio
import time
import uuid as uuid_package
from typing import (
    AsyncGenerator,
    List,
    Optional,
    Set,
    Union,
)

from pydantic import ValidationError

from weaviate.collections.batch.base import (
    ObjectsBatchRequest,
    ReferencesBatchRequest,
    _BatchDataWrapper,
)
from weaviate.collections.batch.grpc_batch import _BatchGRPC
from weaviate.collections.classes.batch import (
    BatchObject,
    BatchObjectReturn,
    BatchReference,
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
    def __init__(self, send: asyncio.Task[None], recv: asyncio.Task[None]) -> None:
        self.send = send
        self.recv = recv


class _BatchBaseAsync:
    def __init__(
        self,
        connection: ConnectionAsync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        objects: Optional[ObjectsBatchRequest[BatchObject]] = None,
        references: Optional[ReferencesBatchRequest] = None,
    ) -> None:
        self.__batch_objects = objects or ObjectsBatchRequest[BatchObject]()
        self.__batch_references = references or ReferencesBatchRequest[BatchReference]()

        self.__connection = connection
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

        self.__uuid_lookup_lock = asyncio.Lock()

        self.__is_shutting_down = asyncio.Event()
        self.__is_shutdown = asyncio.Event()

        self.__objs_cache_lock = asyncio.Lock()
        self.__refs_cache_lock = asyncio.Lock()
        self.__objs_cache: dict[str, BatchObject] = {}
        self.__refs_cache: dict[int, BatchReference] = {}

        self.__stop = False

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
                with self.__objs_cache_lock:
                    logger.warning(
                        f"Re-adding {len(self.__objs_cache)} cached objects to the batch"
                    )
                    await self.__batch_objects.aprepend(list(self.__objs_cache.values()))
                with self.__refs_cache_lock:
                    await self.__batch_references.aprepend(list(self.__refs_cache.values()))
                # start a new stream with a newly reconnected channel
                return await recv_wrapper()

        return _BgTasks(
            send=asyncio.create_task(send_wrapper()), recv=asyncio.create_task(recv_wrapper())
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

    async def __send(self) -> None:
        refresh_time: float = 0.01
        await self.__connection.grpc_batch_stream_write(
            self.__stream, batch_pb2.BatchStreamRequest(start=batch_pb2.BatchStreamRequest.Start())
        )
        while True:
            if len(self.__batch_objects) + len(self.__batch_references) > 0:
                start = time.time()
                while (len_o := len(self.__batch_objects)) + (
                    len_r := len(self.__batch_references)
                ) < self.__batch_size:
                    # wait for more objects to be added up to the batch size
                    await asyncio.sleep(0.01)
                    if time.time() - start >= 1 and (
                        len_o == len(self.__batch_objects) or len_r == len(self.__batch_references)
                    ):
                        # no new objects were added in the last second, exit the loop
                        break

                objs = await self.__batch_objects.apop_items(self.__batch_size)
                refs = await self.__batch_references.apop_items(
                    self.__batch_size - len(objs),
                    uuid_lookup=self.__uuid_lookup,
                )
                async with self.__uuid_lookup_lock:
                    self.__uuid_lookup.difference_update(obj.uuid for obj in objs)

                async for req in self.__generate_stream_requests(objs, refs):
                    logged = False
                    while self.__is_shutting_down.is_set() or self.__is_shutdown.is_set():
                        # if we were shutdown by the node we were connected to, we need to wait for the stream to be restarted
                        # so that the connection is refreshed to a new node where the objects can be accepted
                        # otherwise, we wait until the stream has been started by __batch_stream to send the first batch
                        if not logged:
                            logger.warning("Waiting for stream to be re-established...")
                            logged = True
                            # put sentinel into our queue to signal the end of the current stream
                            await self.__stream.done_writing()
                        await asyncio.sleep(1)
                    if logged:
                        logger.warning("Stream re-established, resuming sending batches")
                    await self.__connection.grpc_batch_stream_write(self.__stream, req)
            elif self.__stop:
                await self.__connection.grpc_batch_stream_write(
                    self.__stream,
                    batch_pb2.BatchStreamRequest(stop=batch_pb2.BatchStreamRequest.Stop()),
                )
                await self.__stream.done_writing()
                logger.warning("Batching finished, sent stop signal to batch stream")
                return
            await asyncio.sleep(refresh_time)

    async def __generate_stream_requests(
        self,
        objects: List[BatchObject],
        references: List[BatchReference],
    ) -> AsyncGenerator[batch_pb2.BatchStreamRequest, None]:
        per_object_overhead = 4  # extra overhead bytes per object in the request

        def request_maker():
            return batch_pb2.BatchStreamRequest()

        request = request_maker()
        total_size = request.ByteSize()

        for object_ in objects:
            obj = self.__batch_grpc.grpc_object(object_._to_internal())
            obj_size = obj.ByteSize() + per_object_overhead

            if total_size + obj_size >= self.__batch_grpc.grpc_max_msg_size:
                await asyncio.sleep(0)  # yield control to event loop
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.objects.values.append(obj)
            total_size += obj_size

        for reference in references:
            ref = self.__batch_grpc.grpc_reference(reference._to_internal())
            ref_size = ref.ByteSize() + per_object_overhead

            if total_size + ref_size >= self.__batch_grpc.grpc_max_msg_size:
                await asyncio.sleep(0)  # yield control to event loop
                yield request
                request = request_maker()
                total_size = request.ByteSize()

            request.data.references.values.append(ref)
            total_size += ref_size

        if len(request.data.objects.values) > 0 or len(request.data.references.values) > 0:
            await asyncio.sleep(0)  # yield control to event loop
            yield request

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
            if message.HasField("results"):
                result_objs = BatchObjectReturn()
                # result_refs = BatchReferenceReturn()
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
                        # TODO: remove cached ref using beacon
                        # self.__refs_cache.pop(success.beacon, None)
                        pass
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
        async with self.__uuid_lookup_lock:
            self.__uuid_lookup.add(uuid)
        await self.__batch_objects.aadd(batch_object)
        async with self.__objs_cache_lock:
            self.__objs_cache[uuid] = batch_object
        self.__objs_count += 1

        while len(self.__batch_objects) >= self.__batch_size * 2:
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
            async with self.__refs_cache_lock:
                self.__refs_cache[self.__refs_count] = batch_reference
                self.__refs_count += 1

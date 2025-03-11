import asyncio
import random
from collections import deque
from typing import Any, Dict, Generator, List, Optional, Union, cast

from grpc.aio import AioRpcError, StreamUnaryCall  # type: ignore
from pydantic import ValidationError

from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.classes.batch import BatchObject, _BatchObject
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import ReferenceInputs
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect import ConnectionV4
from weaviate.connect.base import MAX_GRPC_MESSAGE_LENGTH
from weaviate.exceptions import WeaviateBatchValidationError
from weaviate.event_loop import _EventLoop, Future
from weaviate.proto.v1 import batch_pb2
from weaviate.types import UUID, VECTORS


class _Stream:
    call: StreamUnaryCall[batch_pb2.BatchMessage, batch_pb2.BatchWriteReply]
    __task: Optional[asyncio.Task[None]] = None

    def __init__(self, call: StreamUnaryCall[batch_pb2.BatchMessage, batch_pb2.BatchWriteReply]):
        self.call = call

    async def write(self, message: batch_pb2.BatchMessage) -> None:
        await self.await_task()  # wait for the previous batch to finish if still running, throws an exception here
        self.__task = asyncio.create_task(self.call.write(message))

    async def await_task(self) -> None:
        if self.__task is not None:
            await self.__task
            self.__task = None

    def task_pending(self) -> bool:
        return self.__task is not None


class _Streams:
    streams: Dict[int, _Stream] = {}

    def __init__(self, streams: Dict[int, _Stream]):
        self.streams = streams

    def add(self, stream: _Stream) -> int:
        idx = len(self.streams)
        self.streams[idx] = stream
        return idx

    async def write(self, message: batch_pb2.BatchMessage) -> None:
        if len(self.streams) == 0:
            raise Exception("No streams available")
        while True:
            ready = -1
            for key, stream in self.streams.items():
                # try to find a stream that is ready to write
                if not stream.task_pending():
                    ready = key
                    break
            # if no stream is ready, wait for a random one to finish
            stream = self.streams[
                random.randint(0, len(self.streams) - 1) if ready == -1 else ready
            ]
            await stream.await_task()
            await stream.write(message)
            return

    async def done_writing(self) -> None:
        for stream in self.streams.values():
            await stream.await_task()
        for stream in self.streams.values():
            await stream.call.done_writing()
            # only close one of the streams, it will close all of them lol
            return


class _BatchStreamBase(_BatchGRPC):
    def __init__(
        self,
        connection: ConnectionV4,
    ):
        super().__init__(connection, None)
        self._streams: _Streams = _Streams({})
        self._objs_count = 0
        self._errors: List[batch_pb2.BatchObjectsReply.BatchError] = []
        self._objs: deque[batch_pb2.BatchObject] = deque()
        self._max_batch_size = 1000
        self._max_msg_size = MAX_GRPC_MESSAGE_LENGTH

    @property
    def errors(self) -> List[batch_pb2.BatchObjectsReply.BatchError]:
        """
        Get the list of errors that occurred during the batch operation.

        Returns:
            `List[batch_pb2.BatchObjectsReply.BatchError]`
                The list of errors that occurred during the batch operation.
        """
        return self._errors

    def _add_stream(self) -> None:
        assert self._connection.grpc_stub is not None
        self._streams.add(
            _Stream(
                cast(
                    StreamUnaryCall[batch_pb2.BatchMessage, batch_pb2.BatchWriteReply],
                    self._connection.grpc_stub.BatchWrite(
                        metadata=self._connection.grpc_headers(),
                        timeout=self._connection.timeout_config.insert,
                    ),
                )
            )
        )

    # async def _wait(self) -> None:
    #     async for _ in self._read_replies():
    #         pass

    async def _send(self) -> None:
        try:
            await self._streams.write(
                batch_pb2.BatchMessage(
                    request=batch_pb2.BatchObjectsRequest(objects=self.__batch_generator())
                )
            )
        except AioRpcError as e:
            print(e)

    async def _exit(self) -> None:
        if len(self._objs) > 0:
            await self._send()
        # await self._streams.write(batch_pb2.BatchMessage(sentinel=batch_pb2.BatchStop()))
        await self._streams.done_writing()
        # await self._wait()

    def __batch_generator(self) -> Generator[batch_pb2.BatchObject, None, None]:
        count = 0
        total_bytes = 0
        while len(self._objs) > 0 and count < self._max_batch_size:
            obj = self._objs.popleft()
            total_bytes += obj.ByteSize()
            if total_bytes > self._max_msg_size:
                self._objs.appendleft(obj)
                break
            yield obj
            count += 1

    # async def _read_replies(self) -> AsyncGenerator[batch_pb2.BatchObjectsReply, None]:
    #     assert self._stream is not None
    #     while True:
    #         try:
    #             reply = await self._stream.read()
    #             if reply == EOF:
    #                 return
    #             assert isinstance(reply, batch_pb2.BatchObjectsReply)
    #             self._errors.extend(reply.errors)
    #         except AioRpcError as e:
    #             raise e
    #         yield reply


class _BatchStreamAsync(_BatchStreamBase):
    def __init__(
        self,
        connection: ConnectionV4,
    ):
        super().__init__(connection)

    async def __aenter__(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "_BatchStreamAsync":
        meta = await self._connection.get_meta()
        if "grpcMaxMessageSize" in meta:
            self._max_msg_size = int(meta["grpcMaxMessageSize"])
        for _ in range(2):
            self._add_stream()
        await self._streams.write(
            batch_pb2.BatchMessage(init=batch_pb2.BatchStart(consistency_level=consistency_level))
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self._exit()

    async def __add_object(self, obj: _BatchObject) -> None:
        # if len(self._objs) > 2 * self._max_batch_size:
        #     print("Batch queue length is too long, scaling up concurrency")
        #     # scale up client/server concurrency to reduce the queue length
        #     self._add_stream()
        if len(self._objs) >= self._max_batch_size:
            print(len(self._objs))
            await self._send()
        self._objs.append(self._grpc_object(obj))

    async def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Arguments:
            `collection`
                The name of the collection this object belongs to.
            `properties`
                The data properties of the object to be added as a dictionary.
            `references`
                The references of the object to be added as a dictionary.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will be generated, by default None
            `vector`:
                The embedding of the object. Can be used when a collection does not have a vectorization module or the given
                vector was generated using the _identical_ vectorization module that is configured for the class. In this
                case this vector takes precedence.
                Supported types are
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.
            `tenant`
                The tenant name or Tenant object to be used for this request.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        try:
            batch_object = BatchObject(
                collection=collection,
                properties=properties,
                references=references,
                uuid=uuid,
                vector=vector,
                tenant=tenant,
                index=self._objs_count,
            )
            self._objs_count += 1
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        assert batch_object.uuid is not None
        await self.__add_object(batch_object._to_internal())
        return batch_object.uuid


class _BatchStream(_BatchStreamBase):
    def __init__(self, connection: ConnectionV4, event_loop: _EventLoop):
        super().__init__(connection)
        self.__loop = event_loop
        self.__future: Optional[Future] = None

    def __enter__(self, consistency_level: Optional[ConsistencyLevel] = None) -> "_BatchStream":
        meta = self.__loop.run_until_complete(self._connection.get_meta)
        if "grpcMaxMessageSize" in meta:
            self._max_msg_size = int(meta["grpcMaxMessageSize"])
        self._add_stream()
        self.__loop.run_until_complete(
            self._streams.write,
            batch_pb2.BatchMessage(
                init=batch_pb2.BatchStart(consistency_level=consistency_level, concurrency=2)
            ),
        )
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        if self.__future is not None:
            self.__future.result()  # wait for the previous batch to finish if still running
        self.__loop.run_until_complete(self._exit)

    def __add_object(self, obj: _BatchObject) -> None:
        if len(self._objs) >= self._max_batch_size:
            if self.__future is not None:
                self.__future.result()  # wait for the previous batch to finish if still running
            self.__future = self.__loop.schedule(self._send)
        self._objs.append(self._grpc_object(obj))

    def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Arguments:
            `collection`
                The name of the collection this object belongs to.
            `properties`
                The data properties of the object to be added as a dictionary.
            `references`
                The references of the object to be added as a dictionary.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will be generated, by default None
            `vector`:
                The embedding of the object. Can be used when a collection does not have a vectorization module or the given
                vector was generated using the _identical_ vectorization module that is configured for the class. In this
                case this vector takes precedence.
                Supported types are
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.
            `tenant`
                The tenant name or Tenant object to be used for this request.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        try:
            batch_object = BatchObject(
                collection=collection,
                properties=properties,
                references=references,
                uuid=uuid,
                vector=vector,
                tenant=tenant,
                index=self._objs_count,
            )
            self._objs_count += 1
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        assert batch_object.uuid is not None
        self.__add_object(batch_object._to_internal())
        return batch_object.uuid

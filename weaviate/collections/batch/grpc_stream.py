from typing import Any, AsyncGenerator, List, Optional, Union, cast

from grpc.aio import AioRpcError, EOF, StreamStreamCall  # type: ignore
from pydantic import ValidationError

from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.classes.batch import BatchObject, _BatchObject
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import ReferenceInputs
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateBatchValidationError
from weaviate.proto.v1 import batch_pb2
from weaviate.types import UUID, VECTORS


class _BatchStream(_BatchGRPC):
    def __init__(
        self,
        connection: ConnectionV4,
    ):
        super().__init__(connection, None)
        self.__stream: Optional[
            StreamStreamCall[batch_pb2.BatchMessage, batch_pb2.BatchObjectsReply]
        ] = None
        self.__objs_count = 0
        self.__errors: List[batch_pb2.BatchObjectsReply.BatchError] = []

    @property
    def errors(self) -> List[batch_pb2.BatchObjectsReply.BatchError]:
        """
        Get the list of errors that occurred during the batch operation.

        Returns:
            `List[batch_pb2.BatchObjectsReply.BatchError]`
                The list of errors that occurred during the batch operation.
        """
        return self.__errors

    async def __aenter__(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "_BatchStream":
        assert self._connection.grpc_stub is not None
        self.__stream = cast(
            StreamStreamCall[batch_pb2.BatchMessage, batch_pb2.BatchObjectsReply],
            self._connection.grpc_stub.Batch(
                metadata=self._connection.grpc_headers(),
                timeout=self._connection.timeout_config.insert,
            ),
        )
        await self.__stream.write(
            batch_pb2.BatchMessage(
                init=batch_pb2.BatchStart(consistency_level=consistency_level, concurrency=2)
            )
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        assert self.__stream is not None
        await self.__stream.write(batch_pb2.BatchMessage(sentinel=batch_pb2.BatchStop()))
        await self.__stream.done_writing()
        await self.__wait()

    async def __wait(self) -> None:
        async for _ in self._read_replies():
            pass

    async def _add_object(self, obj: _BatchObject) -> None:
        assert self.__stream is not None
        await self.__stream.write(batch_pb2.BatchMessage(object=self._grpc_object(obj)))

    async def _read_replies(self) -> AsyncGenerator[batch_pb2.BatchObjectsReply, None]:
        assert self.__stream is not None
        while True:
            try:
                reply = await self.__stream.read()
                if reply == EOF:
                    return
                assert isinstance(reply, batch_pb2.BatchObjectsReply)
                self.__errors.extend(reply.errors)
            except AioRpcError as e:
                raise e
            yield reply

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
                index=self.__objs_count,
            )
            self.__objs_count += 1
        except ValidationError as e:
            raise WeaviateBatchValidationError(repr(e))
        assert batch_object.uuid is not None
        await self._add_object(batch_object._to_internal())
        return batch_object.uuid

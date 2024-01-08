from typing import Generic, Optional, Sequence

from weaviate.collections.batch.executor import BatchExecutor
from weaviate.collections.batch.base import _BatchBase
from weaviate.collections.classes.internal import WeaviateReferences, WeaviateReference
from weaviate.collections.classes.types import Properties
from weaviate.connect import HttpxConnection as Connection
from weaviate.types import UUID


class _BatchCollection(Generic[Properties], _BatchBase):
    def __init__(
        self,
        connection: Connection,
        name: str,
        batch_executor: BatchExecutor,
        tenant: Optional[str] = None,
    ) -> None:
        super().__init__(connection, batch_executor)
        self.__name = name
        self.__tenant = tenant

    def add_object(
        self,
        properties: Optional[Properties] = None,
        references: Optional[WeaviateReferences] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be replaced by the new object.

        Arguments:
            `properties`
                The data properties of the object to be added as a dictionary.
            `references`
                The references of the object to be added as a dictionary. Use `wvc.Reference.to` to create the correct values in the dict.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            `vector`:
                The embedding of the object that should be validated. Can be used when a collection does not have a vectorization module or the given vector was generated using the _identical_ vectorization module that is configured for the class. In this case this vector takes precedence. Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        return self._add_object(
            collection=self.__name,
            properties=properties,
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=self.__tenant,
        )

    def add_reference(self, from_uuid: UUID, from_property: str, to: WeaviateReference) -> None:
        """
        Add one reference to this batch.

        Arguments:
            `from_uuid`
                The UUID of the object, as an uuid.UUID object or str, that should reference another object.
                It can be a Weaviate beacon or Weaviate href.
            `from_property`
                The name of the property that contains the reference.
            `to`
                The reference to add, REQUIRED. Use `wvc.Reference.to` to create the correct value.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        for uuid in to.uuids_str:
            self._add_reference(
                from_uuid,
                self.__name,
                from_property,
                uuid,
                to.target_collection if to.is_multi_target else None,
                self.__tenant,
            )

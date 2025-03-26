from abc import abstractmethod
import uuid as uuid_package
from typing import (
    Optional,
    List,
    Sequence,
    Generic,
    Union,
)

from weaviate.collections.classes.batch import (
    DeleteManyObject,
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.data.executor import _DataExecutor
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.types import UUID, VECTORS


class _DataBase(Generic[ConnectionType]):
    # _executor = _DataExecutor()

    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ) -> None:
        self._connection: ConnectionType = connection
        self.name = name
        self._consistency_level = consistency_level
        self._tenant = tenant
        self._validate_arguments = validate_arguments
        self._executor = _DataExecutor(
            weaviate_version=connection._weaviate_version,
            name=name,
            consistency_level=consistency_level,
            tenant=tenant,
            validate_arguments=validate_arguments,
        )

    @abstractmethod
    def insert(
        self,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> ExecutorResult[uuid_package.UUID]:
        """Insert a single object into the collection.

        Arguments:
            `properties`
                The properties of the object, REQUIRED.
            `references`
                Any references to other objects in Weaviate.
            `uuid`
                The UUID of the object. If not provided, a random UUID will be generated.
            `vector`
                The vector(s) of the object.
                Supported types are
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor`, `tf.Tensor`, `pd.Series` and `pl.Series`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.

        Returns:
            `uuid.UUID`, the UUID of the inserted object.

        Raises:
            `weaviate.exceptions.UnexpectedStatusCodeError`:
                If any unexpected error occurs during the insert operation, for example the given UUID already exists.
        """
        raise NotImplementedError()

    @abstractmethod
    def insert_many(
        self,
        objects: Sequence[Union[Properties, DataObject[Properties, Optional[ReferenceInputs]]]],
    ) -> ExecutorResult[BatchObjectReturn]:
        """Insert multiple objects into the collection.

        Arguments:
            `objects`
                The objects to insert. This can be either a list of `Properties` or `DataObject[Properties, ReferenceInputs]`
                    If you didn't set `data_model` then `Properties` will be `Data[str, Any]` in which case you can insert simple dictionaries here.
                        If you want to insert references, vectors, or UUIDs alongside your properties, you will have to use `DataObject` instead.

        Raises:
            `weaviate.exceptions.WeaviateGRPCBatchError`:
                If any unexpected error occurs during the batch operation.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
            `weaviate.exceptions.WeaviateInsertManyAllFailedError`:
                If every object in the batch fails to be inserted. The exception message contains details about the failure.
        """
        raise NotImplementedError()

    @abstractmethod
    def replace(
        self,
        uuid: UUID,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[VECTORS] = None,
    ) -> ExecutorResult[None]:
        """Replace an object in the collection.

        This is equivalent to a PUT operation.

        Arguments:
            `uuid`
                The UUID of the object, REQUIRED.
            `properties`
                The properties of the object, REQUIRED.
            `references`
                Any references to other objects in Weaviate, REQUIRED.
            `vector`
                The vector(s) of the object.
                Supported types are
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor`, `tf.Tensor`, `pd.Series` and `pl.Series`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateInvalidInputError`:
                If any of the arguments are invalid.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        raise NotImplementedError()

    @abstractmethod
    def update(
        self,
        uuid: UUID,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[VECTORS] = None,
    ) -> ExecutorResult[None]:
        """Update an object in the collection.

        This is equivalent to a PATCH operation.

        If the object does not exist yet, it will be created.

        Arguments:
            `uuid`
                The UUID of the object, REQUIRED.
            `properties`
                The properties of the object.
            `references`
                Any references to other objects in Weaviate.
            `vector`
                The vector(s) of the object.
                Supported types are
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor`, `tf.Tensor`, `pd.Series` and `pl.Series`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.
        """
        raise NotImplementedError()

    @abstractmethod
    def reference_add(
        self, from_uuid: UUID, from_property: str, to: SingleReferenceInput
    ) -> ExecutorResult[None]:
        """Create a reference between an object in this collection and any other object in Weaviate.

        Arguments:
            `from_uuid`
                The UUID of the object in this collection, REQUIRED.
            `from_property`
                The name of the property in the object in this collection, REQUIRED.
            `to`
                The reference to add, REQUIRED.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def reference_add_many(
        self, refs: List[DataReferences]
    ) -> ExecutorResult[BatchReferenceReturn]:
        """Create multiple references on a property in batch between objects in this collection and any other object in Weaviate.

        Arguments:
            `refs`
                The references to add including the prop name, from UUID, and to UUID.

        Returns:
            `BatchReferenceReturn`
                A `BatchReferenceReturn` object containing the results of the batch operation.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def reference_delete(
        self, from_uuid: UUID, from_property: str, to: SingleReferenceInput
    ) -> ExecutorResult[None]:
        """Delete a reference from an object within the collection.

        Arguments:
            `from_uuid`
                The UUID of the object in this collection, REQUIRED.
            `from_property`
                The name of the property in the object in this collection from which the reference should be deleted, REQUIRED.
            `to`
                The reference to delete, REQUIRED.
        """
        raise NotImplementedError()

    @abstractmethod
    def reference_replace(
        self, from_uuid: UUID, from_property: str, to: ReferenceInput
    ) -> ExecutorResult[None]:
        """Replace a reference of an object within the collection.

        Arguments:
            `from_uuid`
                The UUID of the object in this collection, REQUIRED.
            `from_property`
                The name of the property in the object in this collection from which the reference should be replaced, REQUIRED.
            `to`
                The reference to replace, REQUIRED.
        """
        raise NotImplementedError()

    @abstractmethod
    def exists(self, uuid: UUID) -> ExecutorResult[bool]:
        """Check for existence of a single object in the collection.

        Arguments:
            `uuid`
                The UUID of the object.

        Returns:
            `bool`, True if objects exists and False if not.

        Raises:
            `weaviate.exceptions.UnexpectedStatusCodeError`:
                If any unexpected error occurs during the operation.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_by_id(self, uuid: UUID) -> ExecutorResult[bool]:
        """Delete an object from the collection based on its UUID.

        Arguments:
            `uuid`
                The UUID of the object to delete, REQUIRED.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_many(
        self, where: _Filters, verbose: bool = False, *, dry_run: bool = False
    ) -> ExecutorResult[Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]]:
        """Delete multiple objects from the collection based on a filter.

        Arguments:
            `where`
                The filter to apply. This filter is the same that is used when performing queries and has the same syntax, REQUIRED.
            `verbose`
                Whether to return the deleted objects in the response.
            `dry_run`
                Whether to perform a dry run. If set to `True`, the objects will not be deleted, but the response will contain the objects that would have been deleted.

        Raises:
            `weaviate.WeaviateConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

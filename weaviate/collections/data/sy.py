import uuid as uuid_package
from typing import Optional, List, Literal, Sequence, Generic, Type, Union, overload

from weaviate.collections.classes.batch import (
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyObject,
    DeleteManyReturn,
)
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.types import Properties, TProperties, _check_properties_generic
from weaviate.collections.data.asy import _DataCollectionAsync
from weaviate.event_loop import _EventLoop
from weaviate.types import UUID, VECTORS


class _DataCollection(Generic[Properties]):
    def __init__(
        self,
        event_loop: _EventLoop,
        data: _DataCollectionAsync[Properties],
    ):
        self.__event_loop = event_loop
        self.__data = data

    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]":
        _check_properties_generic(data_model)
        return _DataCollection[TProperties](
            self.__event_loop,
            self.__data.with_data_model(data_model),
        )

    def delete_by_id(self, uuid: UUID) -> bool:
        """Delete an object from the collection based on its UUID.

        Arguments:
            `uuid`
                The UUID of the object to delete, REQUIRED.
        """
        return self.__event_loop.run_until_complete(self.__data.delete_by_id, uuid)

    def insert(
        self,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> uuid_package.UUID:
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
        return self.__event_loop.run_until_complete(
            self.__data.insert, properties, references, uuid, vector
        )

    def insert_many(
        self,
        objects: Sequence[Union[Properties, DataObject[Properties, Optional[ReferenceInputs]]]],
    ) -> BatchObjectReturn:
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
        return self.__event_loop.run_until_complete(self.__data.insert_many, objects)

    def replace(
        self,
        uuid: UUID,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[VECTORS] = None,
    ) -> None:
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
        return self.__event_loop.run_until_complete(
            self.__data.replace, uuid, properties, references, vector
        )

    def update(
        self,
        uuid: UUID,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[VECTORS] = None,
    ) -> None:
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
        return self.__event_loop.run_until_complete(
            self.__data.update, uuid, properties, references, vector
        )

    def reference_add(self, from_uuid: UUID, from_property: str, to: SingleReferenceInput) -> None:
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
        self.__event_loop.run_until_complete(
            self.__data.reference_add, from_uuid, from_property, to
        )

    def reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
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
        return self.__event_loop.run_until_complete(self.__data.reference_add_many, refs)

    def reference_delete(
        self, from_uuid: UUID, from_property: str, to: SingleReferenceInput
    ) -> None:
        """Delete a reference from an object within the collection.

        Arguments:
            `from_uuid`
                The UUID of the object in this collection, REQUIRED.
            `from_property`
                The name of the property in the object in this collection from which the reference should be deleted, REQUIRED.
            `to`
                The reference to delete, REQUIRED.
        """
        self.__event_loop.run_until_complete(
            self.__data.reference_delete, from_uuid, from_property, to
        )

    def reference_replace(self, from_uuid: UUID, from_property: str, to: ReferenceInput) -> None:
        """Replace a reference of an object within the collection.

        Arguments:
            `from_uuid`
                The UUID of the object in this collection, REQUIRED.
            `from_property`
                The name of the property in the object in this collection from which the reference should be replaced, REQUIRED.
            `to`
                The reference to replace, REQUIRED.
        """
        self.__event_loop.run_until_complete(
            self.__data.reference_replace, from_uuid, from_property, to
        )

    def exists(self, uuid: UUID) -> bool:
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
        return self.__event_loop.run_until_complete(self.__data.exists, uuid)

    @overload
    def delete_many(
        self, where: _Filters, verbose: Literal[False] = ..., *, dry_run: bool = False
    ) -> DeleteManyReturn[None]:
        ...

    @overload
    def delete_many(
        self, where: _Filters, verbose: Literal[True], *, dry_run: bool = False
    ) -> DeleteManyReturn[List[DeleteManyObject]]:
        ...

    @overload
    def delete_many(
        self, where: _Filters, verbose: bool = ..., *, dry_run: bool = False
    ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]:
        ...

    def delete_many(
        self, where: _Filters, verbose: bool = False, *, dry_run: bool = False
    ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]:
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
        return self.__event_loop.run_until_complete(
            self.__data.delete_many, where, verbose, dry_run=dry_run
        )

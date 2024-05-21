import uuid as uuid_package
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Literal,
    Mapping,
    Sequence,
    Generic,
    Type,
    Union,
    cast,
    overload,
)

from weaviate.collections.classes.batch import (
    DeleteManyObject,
    _BatchObject,
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    _Reference,
    ReferenceToMulti,
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
    _check_properties_generic,
)
from weaviate.collections.data.base import _Data
from weaviate.connect import ConnectionV4
from weaviate.types import UUID, VECTORS
from weaviate.util import _get_vector_v4
from weaviate.validator import _validate_input, _ValidateArgument


class _DataCollectionAsync(Generic[Properties], _Data):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
        type_: Optional[Type[Properties]] = None,
    ):
        super().__init__(connection, name, consistency_level, tenant, validate_arguments)
        self.__type = type_

    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollectionAsync[TProperties]":
        _check_properties_generic(data_model)
        return _DataCollectionAsync[TProperties](
            self._connection,
            self.name,
            self._consistency_level,
            self._tenant,
            self._validate_arguments,
            data_model,
        )

    def __parse_vector(self, obj: Dict[str, Any], vector: VECTORS) -> Dict[str, Any]:
        if isinstance(vector, dict):
            obj["vectors"] = {key: _get_vector_v4(val) for key, val in vector.items()}
        else:
            obj["vector"] = _get_vector_v4(vector)
        return obj

    async def insert(
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID, None], name="uuid", value=uuid),
                    _ValidateArgument(expected=[Mapping], name="properties", value=properties),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                ],
            )
        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": {**props, **refs},
            "id": str(uuid if uuid is not None else uuid_package.uuid4()),
        }
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        return await self._insert(weaviate_obj)

    async def insert_many(
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
        return await self._batch_grpc.objects(
            [
                (
                    _BatchObject(
                        collection=self.name,
                        vector=obj.vector,
                        uuid=str(obj.uuid if obj.uuid is not None else uuid_package.uuid4()),
                        properties=cast(dict, obj.properties),
                        tenant=self._tenant,
                        references=obj.references,
                    )
                    if isinstance(obj, DataObject)
                    else _BatchObject(
                        collection=self.name,
                        vector=None,
                        uuid=str(uuid_package.uuid4()),
                        properties=cast(dict, obj),
                        tenant=self._tenant,
                        references=None,
                    )
                )
                for obj in objects
            ],
            timeout=self._connection.timeout_config.insert,
        )

    async def replace(
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="uuid", value=uuid),
                    _ValidateArgument(expected=[Mapping], name="properties", value=properties),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                ]
            )
        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": {**props, **refs},
        }
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        await self._replace(weaviate_obj, uuid=uuid)

    async def update(
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="uuid", value=uuid),
                    _ValidateArgument(
                        expected=[Mapping, None], name="properties", value=properties
                    ),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                ],
            )
        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {"class": self.name, "properties": {**props, **refs}}
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        await self._update(weaviate_obj, uuid=uuid)

    async def reference_add(
        self, from_uuid: UUID, from_property: str, to: SingleReferenceInput
    ) -> None:
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="from_uuid", value=from_uuid),
                    _ValidateArgument(expected=[str], name="from_property", value=from_property),
                    _ValidateArgument(
                        expected=[UUID, ReferenceToMulti], name="references", value=to
                    ),
                ],
            )
        if isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)
        await self._reference_add(from_uuid=from_uuid, from_property=from_property, ref=ref)

    async def reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
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
        return await self._reference_add_many(refs)

    async def reference_delete(
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="from_uuid", value=from_uuid),
                    _ValidateArgument(expected=[str], name="from_property", value=from_property),
                    _ValidateArgument(
                        expected=[UUID, ReferenceToMulti], name="references", value=to
                    ),
                ]
            )
        if isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)
        await self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

    async def reference_replace(
        self, from_uuid: UUID, from_property: str, to: ReferenceInput
    ) -> None:
        """Replace a reference of an object within the collection.

        Arguments:
            `from_uuid`
                The UUID of the object in this collection, REQUIRED.
            `from_property`
                The name of the property in the object in this collection from which the reference should be replaced, REQUIRED.
            `to`
                The reference to replace, REQUIRED.
        """
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="from_uuid", value=from_uuid),
                    _ValidateArgument(expected=[str], name="from_property", value=from_property),
                    _ValidateArgument(
                        expected=[
                            UUID,
                            ReferenceToMulti,
                            List[str],
                            List[uuid_package.UUID],
                            List[UUID],
                        ],
                        name="references",
                        value=to,
                    ),
                ]
            )
        if isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)
        await self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)

    async def exists(self, uuid: UUID) -> bool:
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
        _validate_input(_ValidateArgument(expected=[UUID], name="uuid", value=uuid))
        return await self._exists(str(uuid))

    @overload
    async def delete_many(
        self, where: _Filters, verbose: Literal[False] = ..., *, dry_run: bool = False
    ) -> DeleteManyReturn[None]:
        ...

    @overload
    async def delete_many(
        self, where: _Filters, verbose: Literal[True], *, dry_run: bool = False
    ) -> DeleteManyReturn[List[DeleteManyObject]]:
        ...

    @overload
    async def delete_many(
        self, where: _Filters, verbose: bool = ..., *, dry_run: bool = False
    ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]:
        ...

    async def delete_many(
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
        _ValidateArgument(expected=[_Filters], name="where", value=where)
        return await self._batch_delete_grpc.batch_delete(
            self.name, where, verbose, dry_run, self._tenant
        )

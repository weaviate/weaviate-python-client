import datetime
import uuid as uuid_package
from typing import (
    Dict,
    Any,
    Literal,
    Optional,
    List,
    Mapping,
    Tuple,
    Sequence,
    Generic,
    Type,
    Union,
    cast,
    overload,
)

from weaviate.collections.batch.grpc_batch_delete import _BatchDeleteGRPC
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.batch.rest import _BatchREST
from weaviate.collections.classes.batch import (
    DeleteManyObject,
    _BatchObject,
    BatchObjectReturn,
    _BatchReference,
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
    GeoCoordinate,
    PhoneNumber,
    _PhoneNumber,
    Properties,
    TProperties,
    WeaviateField,
    _check_properties_generic,
)
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.types import BEACON, UUID, VECTORS
from weaviate.util import (
    _datetime_to_string,
    _get_vector_v4,
)
from weaviate.validator import _validate_input, _ValidateArgument


class _Data:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ) -> None:
        self._connection = connection
        self.name = name
        self._consistency_level = consistency_level
        self._tenant = tenant
        self._validate_arguments = validate_arguments
        self._batch_grpc = _BatchGRPC(connection, consistency_level)
        self._batch_delete_grpc = _BatchDeleteGRPC(connection, consistency_level)
        self._batch_rest = _BatchREST(connection, consistency_level)

    def _insert(self, weaviate_obj: Dict[str, Any]) -> uuid_package.UUID:
        path = "/objects"

        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        self._connection.post(
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not added",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="insert object"),
        )
        return uuid_package.UUID(weaviate_obj["id"])

    def _exists(self, uuid: str) -> bool:
        path = "/objects/" + self.name + "/" + uuid

        params = self.__apply_context({})
        request = self._connection.head(
            path=path,
            params=params,
            error_msg="object existence",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="object existence"),
        )
        return request.status_code == 204

    def delete_by_id(self, uuid: UUID) -> bool:
        """Delete an object from the collection based on its UUID.

        Arguments:
            `uuid`
                The UUID of the object to delete, REQUIRED.
        """
        path = f"/objects/{self.name}/{uuid}"

        response = self._connection.delete(
            path=path,
            params=self.__apply_context({}),
            error_msg="Object could not be deleted.",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="delete object"),
        )
        if response.status_code == 204:
            return True  # Successfully deleted
        else:
            assert response.status_code == 404
            return False  # did not exist

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
        _ValidateArgument(expected=[_Filters], name="where", value=where)
        return self._batch_delete_grpc.batch_delete(
            self.name, where, verbose, dry_run, self._tenant
        )

    def _replace(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        weaviate_obj["id"] = str(uuid)  # must add ID to payload for PUT request

        self._connection.put(
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not replaced.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="replace object"),
        )

    def _update(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        self._connection.patch(
            path=path,
            weaviate_object=weaviate_obj,
            params=params,
            error_msg="Object was not updated.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 204], error="update object"),
        )

    def _reference_add(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_add does not support adding multiple objects to a reference at once. Use reference_add_many or reference_replace instead."
            )
        for beacon in ref._to_beacons():
            self._connection.post(
                path=path,
                weaviate_object=beacon,
                params=self.__apply_context(params),
                error_msg="Reference was not added.",
                status_codes=_ExpectedStatusCodes(ok_in=200, error="add reference to object"),
            )

    def _reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
        batch = [
            _BatchReference(
                from_=f"{BEACON}{self.name}/{ref.from_uuid}/{ref.from_property}",
                to=beacon,
                tenant=self._tenant,
                from_uuid=str(ref.from_uuid),
            )
            for ref in refs
            for beacon in ref._to_beacons()
        ]
        return self._batch_rest.references(list(batch))

    def _reference_delete(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_delete does not support deleting multiple objects from a reference at once. Use reference_replace instead."
            )
        for beacon in ref._to_beacons():
            self._connection.delete(
                path=path,
                weaviate_object=beacon,
                params=self.__apply_context(params),
                error_msg="Reference was not deleted.",
                status_codes=_ExpectedStatusCodes(ok_in=204, error="delete reference from object"),
            )

    def _reference_replace(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
        self._connection.put(
            path=path,
            weaviate_object=ref._to_beacons(),
            params=self.__apply_context(params),
            error_msg="Reference was not replaced.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="replace reference on object"),
        )

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._tenant is not None:
            params["tenant"] = self._tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level.value
        return params

    def __apply_context_to_params_and_object(
        self, params: Dict[str, Any], obj: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self._tenant is not None:
            obj["tenant"] = self._tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level.value
        return params, obj

    def _serialize_props(self, props: Properties) -> Dict[str, Any]:
        return {key: self.__serialize_primitive(val) for key, val in props.items()}

    def _serialize_refs(self, refs: ReferenceInputs) -> Dict[str, Any]:
        return {
            key: (
                val._to_beacons()
                if isinstance(val, _Reference) or isinstance(val, ReferenceToMulti)
                else _Reference(target_collection=None, uuids=val)._to_beacons()
            )
            for key, val in refs.items()
        }

    def __serialize_primitive(self, value: WeaviateField) -> Any:
        if isinstance(value, str) or isinstance(value, int) or isinstance(value, float):
            return value
        if isinstance(value, uuid_package.UUID):
            return str(value)
        if isinstance(value, datetime.datetime):
            return _datetime_to_string(value)
        if isinstance(value, GeoCoordinate):
            return value._to_dict()
        if isinstance(value, PhoneNumber):
            return value._to_dict()
        if isinstance(value, _PhoneNumber):
            raise WeaviateInvalidInputError(
                "Cannot use _PhoneNumber when inserting a phone number. Use PhoneNumber instead."
            )
        if isinstance(value, Mapping):
            return {key: self.__serialize_primitive(val) for key, val in value.items()}
        if isinstance(value, Sequence):
            return [self.__serialize_primitive(val) for val in value]
        if value is None:
            return value
        raise WeaviateInvalidInputError(
            f"Cannot serialize value of type {type(value)} to Weaviate."
        )


class _DataCollection(Generic[Properties], _Data):
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

    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]":
        _check_properties_generic(data_model)
        return _DataCollection[TProperties](
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID, None], name="uuid", value=uuid),
                    _ValidateArgument(expected=[Mapping], name="properties", value=properties),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                    _ValidateArgument(
                        expected=[Sequence, None, Mapping], name="vector", value=vector
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

        return self._insert(weaviate_obj)

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
        return self._batch_grpc.objects(
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(expected=[UUID], name="uuid", value=uuid),
                    _ValidateArgument(expected=[Mapping], name="properties", value=properties),
                    _ValidateArgument(
                        expected=[Mapping, None], name="references", value=references
                    ),
                    _ValidateArgument(
                        expected=[Sequence, None, Mapping], name="vector", value=vector
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

        self._replace(weaviate_obj, uuid=uuid)

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
                    _ValidateArgument(
                        expected=[Sequence, None, Mapping], name="vector", value=vector
                    ),
                ],
            )
        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {"class": self.name, "properties": {**props, **refs}}
        if vector is not None:
            weaviate_obj = self.__parse_vector(weaviate_obj, vector)

        self._update(weaviate_obj, uuid=uuid)

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
        self._reference_add(from_uuid=from_uuid, from_property=from_property, ref=ref)

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
        return self._reference_add_many(refs)

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
        self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

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
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)

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
        _validate_input(_ValidateArgument(expected=[UUID], name="uuid", value=uuid))
        return self._exists(str(uuid))

import datetime
import uuid as uuid_package
from typing import (
    Dict,
    Any,
    Literal,
    Optional,
    List,
    Tuple,
    Sequence,
    Generic,
    Type,
    Union,
    cast,
    overload,
)

from requests.exceptions import ConnectionError as RequestsConnectionError
from weaviate.collections.batch.grpc_batch_delete import _BatchDeleteGRPC

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
from weaviate.collections.classes.internal import (
    _Reference,
    Object,
    _metadata_from_dict,
    ReferenceToMulti,
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.orm import (
    Model,
)
from weaviate.collections.classes.types import (
    GeoCoordinate,
    PhoneNumber,
    Properties,
    TProperties,
    _check_properties_generic,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC, _validate_props
from weaviate.collections.batch.rest import _BatchREST
from weaviate.collections.validator import _raise_invalid_input
from weaviate.connect import ConnectionV4
from weaviate.exceptions import (
    UnexpectedStatusCodeError,
    ObjectAlreadyExistsError,
    WeaviateInvalidInputError,
)
from weaviate.util import (
    _datetime_to_string,
    _decode_json_response_dict,
    get_vector,
)
from weaviate.types import BEACON, UUID


class _Data:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ) -> None:
        self._connection = connection
        self.name = name
        self._consistency_level = consistency_level
        self._tenant = tenant
        self._batch_grpc = _BatchGRPC(connection, consistency_level)
        self._batch_delete_grpc = _BatchDeleteGRPC(connection, consistency_level)
        self._batch_rest = _BatchREST(connection, consistency_level)

    def _insert(self, weaviate_obj: Dict[str, Any], clean_props: bool) -> uuid_package.UUID:
        path = "/objects"
        _validate_props(weaviate_obj["properties"], clean_props=clean_props)

        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not added to Weaviate.") from conn_err
        if response.status_code == 200:
            return uuid_package.UUID(weaviate_obj["id"])

        try:
            response_json = _decode_json_response_dict(response, "insert object")
            assert response_json is not None
            if "already exists" in response_json["error"][0]["message"]:
                raise ObjectAlreadyExistsError(weaviate_obj["id"])
        except KeyError:
            pass
        raise UnexpectedStatusCodeError("Creating object", response)

    def delete_by_id(self, uuid: UUID) -> bool:
        """Delete an object from the collection based on its UUID.

        Arguments:
            `uuid`
                The UUID of the object to delete, REQUIRED.
        """
        path = f"/objects/{self.name}/{uuid}"

        try:
            response = self._connection.delete(path=path, params=self.__apply_context({}))
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object could not be deleted.") from conn_err
        if response.status_code == 204:
            return True  # Successfully deleted
        elif response.status_code == 404:
            return False  # did not exist
        raise UnexpectedStatusCodeError("Delete object", response)

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
            `requests.ConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
        """
        if not isinstance(where, _Filters):
            _raise_invalid_input("where", where, _Filters)
        return self._batch_delete_grpc.batch_delete(
            self.name, where, verbose, dry_run, self._tenant
        )

    def _replace(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        weaviate_obj["id"] = str(uuid)  # must add ID to payload for PUT request

        try:
            response = self._connection.put(path=path, weaviate_object=weaviate_obj, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not replaced.") from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeError("Replacing object", response)

    def _update(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        try:
            response = self._connection.patch(
                path=path, weaviate_object=weaviate_obj, params=params
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not updated.") from conn_err
        if response.status_code == 204 or response.status_code == 200:
            return
        raise UnexpectedStatusCodeError("Update object", response)

    def _reference_add(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"

        if ref.is_one_to_many:
            raise WeaviateInvalidInputError(
                "reference_add does not support adding multiple objects to a reference at once. Use reference_add_many or reference_replace instead."
            )
        for beacon in ref._to_beacons():
            try:
                response = self._connection.post(
                    path=path,
                    weaviate_object=beacon,
                    params=self.__apply_context(params),
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError("Reference was not added.") from conn_err
            if response.status_code != 200:
                raise UnexpectedStatusCodeError("Add property reference to object", response)

    def _reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
        batch = [
            _BatchReference(
                from_=f"{BEACON}{self.name}/{ref.from_uuid}/{ref.from_property}",
                to=beacon,
                tenant=self._tenant,
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
            try:
                response = self._connection.delete(
                    path=path,
                    weaviate_object=beacon,
                    params=self.__apply_context(params),
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError("Reference was not added.") from conn_err
            if response.status_code != 204:
                raise UnexpectedStatusCodeError("Add property reference to object", response)

    def _reference_replace(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
        try:
            response = self._connection.put(
                path=path,
                weaviate_object=ref._to_beacons(),
                params=self.__apply_context(params),
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Reference was not added.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeError("Add property reference to object", response)

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
            key: val._to_beacons()
            if isinstance(val, _Reference) or isinstance(val, ReferenceToMulti)
            else _Reference(target_collection=None, uuids=val)._to_beacons()
            for key, val in refs.items()
        }

    def __serialize_primitive(self, value: Any) -> Any:
        if isinstance(value, uuid_package.UUID):
            return str(value)
        if isinstance(value, datetime.datetime):
            return _datetime_to_string(value)
        if isinstance(value, list):
            return [self.__serialize_primitive(val) for val in value]
        if isinstance(value, GeoCoordinate):
            return value._to_dict()
        if isinstance(value, PhoneNumber):
            return value._to_dict()
        return value


class _DataCollection(Generic[Properties], _Data):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        type_: Optional[Type[Properties]] = None,
    ):
        super().__init__(connection, name, consistency_level, tenant)
        self.__type = type_

    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]":
        _check_properties_generic(data_model)
        return _DataCollection[TProperties](
            self._connection, self.name, self._consistency_level, self._tenant, data_model
        )

    def insert(
        self,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[List[float]] = None,
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
                The vector of the object.
        """
        if not isinstance(properties, dict):
            _raise_invalid_input("properties", properties, dict)
        if references is not None and not isinstance(references, dict):
            _raise_invalid_input("references", references, dict)

        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": {**props, **refs},
            "id": str(uuid if uuid is not None else uuid_package.uuid4()),
        }

        if vector is not None:
            weaviate_obj["vector"] = get_vector(vector)

        return self._insert(weaviate_obj, False)

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
                _BatchObject(
                    collection=self.name,
                    vector=obj.vector,
                    uuid=obj.uuid,
                    properties=cast(dict, obj.properties),
                    tenant=self._tenant,
                    references=obj.references,
                )
                if isinstance(obj, DataObject)
                else _BatchObject(
                    collection=self.name,
                    vector=None,
                    uuid=None,
                    properties=cast(dict, obj),
                    tenant=None,
                    references=None,
                )
                for obj in objects
            ],
            timeout=self._connection.timeout_config.connect,
        )

    def replace(
        self,
        uuid: UUID,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[List[float]] = None,
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
                The vector of the object.

        Raises:
            `requests.ConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        if not isinstance(properties, dict):
            _raise_invalid_input("properties", properties, dict)
        if references is not None and not isinstance(references, dict):
            _raise_invalid_input("references", references, dict)

        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": {**props, **refs},
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._replace(weaviate_obj, uuid=uuid)

    def update(
        self,
        uuid: UUID,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[List[float]] = None,
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
                The vector of the object.
        """
        if properties is not None and not isinstance(properties, dict):
            _raise_invalid_input("properties", properties, dict)
        if references is not None and not isinstance(references, dict):
            _raise_invalid_input("references", references, dict)

        props = self._serialize_props(properties) if properties is not None else {}
        refs = self._serialize_refs(references) if references is not None else {}
        weaviate_obj: Dict[str, Any] = {"class": self.name, "properties": {**props, **refs}}
        if vector is not None:
            weaviate_obj["vector"] = vector

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
            `requests.ConnectionError`:
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`:
                If Weaviate reports a non-OK status.
        """
        if (
            not isinstance(to, str)
            and not isinstance(to, uuid_package.UUID)
            and not isinstance(to, ReferenceToMulti)
            and not isinstance(to, _Reference)
        ):
            _raise_invalid_input("to", to, SingleReferenceInput)
        if isinstance(to, _Reference):
            ref = to
        elif isinstance(to, ReferenceToMulti):
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
            `requests.ConnectionError`:
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
        if (
            not isinstance(to, str)
            and not isinstance(to, uuid_package.UUID)
            and not isinstance(to, ReferenceToMulti)
            and not isinstance(to, _Reference)
        ):
            _raise_invalid_input("to", to, SingleReferenceInput)
        if isinstance(to, _Reference):
            ref = to
        elif isinstance(to, ReferenceToMulti):
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
        if (
            not isinstance(to, str)
            and not isinstance(to, uuid_package.UUID)
            and not isinstance(to, _Reference)
            and not isinstance(to, Sequence)
            and not isinstance(to, ReferenceToMulti)
        ):
            _raise_invalid_input("to", to, ReferenceInput)
        if isinstance(to, _Reference):
            ref = to
        elif isinstance(to, ReferenceToMulti):
            ref = _Reference(target_collection=to.target_collection, uuids=to.uuids)
        else:
            ref = _Reference(target_collection=None, uuids=to)
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)


class _DataCollectionModel(Generic[Model], _Data):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        model: Type[Model],
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        super().__init__(connection, name, consistency_level, tenant)
        self.__model = model

    def _json_to_object(self, obj: Dict[str, Any]) -> Object[Model, dict]:
        for ref in self.__model.get_ref_fields(self.__model):
            if ref not in obj["properties"]:
                continue

            beacons = obj["properties"][ref]
            uuids = []
            for beacon in beacons:
                uri = beacon["beacon"]
                assert isinstance(uri, str)
                uuids.append(uri.split("/")[-1])

            obj["properties"][ref] = uuids

        # weaviate does not save none values, so we need to add them to pass model validation
        for prop in self.__model.get_non_default_fields(self.__model):
            if prop not in obj["properties"]:
                obj["properties"][prop] = None

        uuid, vector, metadata = _metadata_from_dict(obj)
        model_object = Object[Model, dict](
            collection=self.name,
            properties=self.__model.model_validate(
                {
                    **obj["properties"],
                    "uuid": uuid,
                    "vector": vector,
                }
            ),
            references={},
            metadata=metadata,
            uuid=uuid,
            vector=vector,
        )
        return model_object

    def insert(self, obj: Model) -> uuid_package.UUID:
        self.__model.model_validate(obj)
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_props(obj.props_to_dict()),
            "id": str(obj.uuid),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._insert(weaviate_obj, False)
        return uuid_package.UUID(str(obj.uuid))

    def insert_many(self, objects: List[Model]) -> BatchObjectReturn:
        for obj in objects:
            self.__model.model_validate(obj)

        data_objects = [
            _BatchObject(
                collection=self.name,
                properties=obj.props_to_dict(),
                tenant=self._tenant,
                uuid=obj.uuid,
                vector=obj.vector,
                references=None,
            )
            for obj in objects
        ]

        return self._batch_grpc.objects(data_objects, self._connection.timeout_config.connect)

    def replace(self, obj: Model, uuid: UUID) -> None:
        self.__model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_props(obj.props_to_dict()),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._replace(weaviate_obj, uuid)

    def update(self, obj: Model, uuid: UUID) -> None:
        self.__model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_props(obj.props_to_dict()),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._update(weaviate_obj, uuid)

    def reference_add(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        self._reference_add(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_delete(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_replace(self, from_uuid: UUID, from_property: str, ref: _Reference) -> None:
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn:
        return self._reference_add_many(refs)

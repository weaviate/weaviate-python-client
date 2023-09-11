import datetime
import uuid as uuid_package
from typing import (
    Dict,
    Any,
    Optional,
    List,
    Tuple,
    Generic,
    Type,
    cast,
    get_type_hints,
    get_origin,
)

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes.batch import (
    _BatchObject,
    _BatchObjectReturn,
    _BatchReference,
    _BatchReferenceReturn,
)
from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.classes.data import (
    DataObject,
    DataReference,
    GetObjectByIdMetadata,
    GetObjectsMetadata,
    IncludesModel,
)
from weaviate.collection.classes.internal import _Object, _metadata_from_dict, Reference
from weaviate.collection.classes.orm import (
    Model,
)
from weaviate.collection.classes.types import Properties, TProperties, _check_data_model
from weaviate.collection.grpc_batch import _BatchGRPC
from weaviate.connect import Connection
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    ObjectAlreadyExistsException,
)
from weaviate.util import _datetime_to_string
from weaviate.weaviate_types import BEACON, UUID


class _Data:
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ) -> None:
        self._connection = connection
        self.name = name
        self._consistency_level = consistency_level
        self._tenant = tenant
        self._batch = _BatchGRPC(connection, consistency_level)

    def _insert(self, weaviate_obj: Dict[str, Any]) -> uuid_package.UUID:
        path = "/objects"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not added to Weaviate.") from conn_err
        if response.status_code == 200:
            return uuid_package.UUID(weaviate_obj["id"])

        try:
            if "already exists" in response.json()["error"][0]["message"]:
                raise ObjectAlreadyExistsException(weaviate_obj["id"])
        except KeyError:
            pass
        raise UnexpectedStatusCodeException("Creating object", response)

    def delete(self, uuid: UUID) -> bool:
        path = f"/objects/{self.name}/{uuid}"

        try:
            response = self._connection.delete(path=path, params=self.__apply_context({}))
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object could not be deleted.") from conn_err
        if response.status_code == 204:
            return True  # Successfully deleted
        elif response.status_code == 404:
            return False  # did not exist
        raise UnexpectedStatusCodeException("Delete object", response)

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
        raise UnexpectedStatusCodeException("Replacing object", response)

    def _update(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self.name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        try:
            response = self._connection.patch(
                path=path, weaviate_object=weaviate_obj, params=params
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not updated.") from conn_err
        if response.status_code == 204:
            return
        raise UnexpectedStatusCodeException("Update object", response)

    def _get_by_id(
        self, uuid: UUID, metadata: Optional[GetObjectByIdMetadata]
    ) -> Optional[Dict[str, Any]]:
        path = f"/objects/{self.name}/{uuid}"

        return self._get_from_weaviate(
            params=self.__apply_context({}), path=path, includes=metadata
        )

    def _get(
        self, limit: Optional[int], metadata: Optional[GetObjectsMetadata]
    ) -> Optional[Dict[str, Any]]:
        path = "/objects"
        params: Dict[str, Any] = {"class": self.name}
        if limit is not None:
            params["limit"] = limit

        return self._get_from_weaviate(
            params=self.__apply_context(params), path=path, includes=metadata
        )

    def _get_from_weaviate(
        self, params: Dict[str, Any], path: str, includes: Optional[IncludesModel]
    ) -> Optional[Dict[str, Any]]:
        if includes is not None:
            params["include"] = includes.to_include()
        try:
            response = self._connection.get(path=path, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not get object/s.") from conn_err
        if response.status_code == 200:
            return_dict: Dict[str, Any] = response.json()
            return return_dict
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Get object/s", response)

    def _reference_add(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
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
                raise UnexpectedStatusCodeException("Add property reference to object", response)

    def _reference_delete(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
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
                raise UnexpectedStatusCodeException("Add property reference to object", response)

    def _reference_replace(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
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
            raise UnexpectedStatusCodeException("Add property reference to object", response)

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._tenant is not None:
            params["tenant"] = self._tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level
        return params

    def __apply_context_to_params_and_object(
        self, params: Dict[str, Any], obj: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self._tenant is not None:
            obj["tenant"] = self._tenant
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level
        return params, obj

    def _serialize_properties(self, data: Properties) -> Dict[str, Any]:
        return {
            key: val._to_beacons()
            if isinstance(val, Reference)
            else self.__serialize_primitive(val)
            for key, val in data.items()
        }

    def __serialize_primitive(self, value: Any) -> Any:
        if isinstance(value, uuid_package.UUID):
            return str(value)
        if isinstance(value, datetime.datetime):
            return _datetime_to_string(value)
        if isinstance(value, list):
            return [self.__serialize_primitive(val) for val in value]
        return value

    def _deserialize_primitive(self, value: Any, type_value: Optional[Any]) -> Any:
        if type_value is None:
            return value
        if type_value == uuid_package.UUID:
            return uuid_package.UUID(value)
        if type_value == datetime.datetime:
            return datetime.datetime.fromisoformat(value)
        if isinstance(type_value, list):
            return [
                self._deserialize_primitive(val, type_value[idx]) for idx, val in enumerate(value)
            ]
        return value


class _DataCollection(Generic[Properties], _Data):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        type_: Optional[Type[Properties]] = None,
    ):
        super().__init__(connection, name, consistency_level, tenant)
        self.__type = type_

    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]":
        _check_data_model(data_model)
        return _DataCollection[TProperties](
            self._connection, self.name, self._consistency_level, self._tenant, data_model
        )

    def __deserialize_properties(self, data: Dict[str, Any]) -> Properties:
        hints = (
            get_type_hints(self.__type)
            if self.__type and not get_origin(self.__type) == dict
            else {}
        )
        return cast(
            Properties,
            {key: self._deserialize_primitive(val, hints.get(key)) for key, val in data.items()},
        )

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object[Properties]:
        props = self.__deserialize_properties(obj["properties"])
        return _Object(
            properties=cast(Properties, props),
            metadata=_metadata_from_dict(obj),
        )

    def insert(
        self,
        properties: Properties,
        uuid: Optional[UUID] = None,
        vector: Optional[List[float]] = None,
    ) -> uuid_package.UUID:
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_properties(properties),
            "id": str(uuid if uuid is not None else uuid_package.uuid4()),
        }

        if vector is not None:
            weaviate_obj["vector"] = vector

        return self._insert(weaviate_obj)

    def insert_many(self, objects: List[DataObject[Properties]]) -> _BatchObjectReturn:
        data_objects = [
            _BatchObject(
                class_name=self.name,
                properties=cast(dict, obj.properties),
                tenant=self._tenant,
                vector=obj.vector,
                uuid=obj.uuid,
            )
            for obj in objects
        ]
        return self._batch.objects(data_objects)

    def replace(
        self, properties: Properties, uuid: UUID, vector: Optional[List[float]] = None
    ) -> None:
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_properties(properties),
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._replace(weaviate_obj, uuid=uuid)

    def update(
        self, properties: Properties, uuid: UUID, vector: Optional[List[float]] = None
    ) -> None:
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_properties(properties),
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._update(weaviate_obj, uuid=uuid)

    def get_by_id(
        self, uuid: UUID, metadata: Optional[GetObjectByIdMetadata] = None
    ) -> Optional[_Object[Properties]]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return ret
        return self._json_to_object(ret)

    def get(
        self, limit: Optional[int] = None, metadata: Optional[GetObjectsMetadata] = None
    ) -> List[_Object[Properties]]:
        ret = self._get(limit=limit, metadata=metadata)
        if ret is None:
            return []

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        self._reference_add(
            from_uuid=from_uuid,
            from_property=from_property,
            ref=ref,
        )

    def reference_batch(self, references: List[DataReference]) -> _BatchReferenceReturn:
        refs = [
            _BatchReference(
                from_=BEACON + f"{self.name}/{ref.from_uuid}/{ref.from_property}",
                to=BEACON + str(ref.to_uuid),
                tenant=self._tenant,
            )
            for ref in references
        ]
        return self._batch.references(refs)

    def reference_delete(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_replace(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)


class _DataCollectionModel(Generic[Model], _Data):
    def __init__(
        self,
        connection: Connection,
        name: str,
        model: Type[Model],
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        super().__init__(connection, name, consistency_level, tenant)
        self.__model = model

    def _json_to_object(self, obj: Dict[str, Any]) -> _Object[Model]:
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

        metadata = _metadata_from_dict(obj)
        model_object = _Object[Model](
            properties=self.__model.model_validate(
                {
                    **obj["properties"],
                    "uuid": metadata.uuid,
                    "vector": metadata.vector,
                }
            ),
            metadata=metadata,
        )
        return model_object

    def insert(self, obj: Model) -> uuid_package.UUID:
        self.__model.model_validate(obj)
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_properties(obj.props_to_dict()),
            "id": str(obj.uuid),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._insert(weaviate_obj)
        return uuid_package.UUID(str(obj.uuid))

    def insert_many(self, objects: List[Model]) -> _BatchObjectReturn:
        for obj in objects:
            self.__model.model_validate(obj)

        data_objects = [
            _BatchObject(
                class_name=self.name,
                properties=obj.props_to_dict(),
                tenant=self._tenant,
                uuid=obj.uuid,
                vector=obj.vector,
            )
            for obj in objects
        ]

        return self._batch.objects(data_objects)

    def replace(self, obj: Model, uuid: UUID) -> None:
        self.__model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_properties(obj.props_to_dict()),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._replace(weaviate_obj, uuid)

    def update(self, obj: Model, uuid: UUID) -> None:
        self.__model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._serialize_properties(obj.props_to_dict()),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._update(weaviate_obj, uuid)

    def get_by_id(
        self, uuid: UUID, metadata: Optional[GetObjectByIdMetadata] = None
    ) -> Optional[_Object[Model]]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return None
        return self._json_to_object(ret)

    def get(
        self, limit: Optional[int] = None, metadata: Optional[GetObjectsMetadata] = None
    ) -> List[_Object[Model]]:
        ret = self._get(limit=limit, metadata=metadata)
        if ret is None:
            return []

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        self._reference_add(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_delete(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_replace(self, from_uuid: UUID, from_property: str, ref: Reference) -> None:
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_add_many(
        self, from_property: str, refs: List[_BatchReference]
    ) -> _BatchReferenceReturn:
        return self._batch.references(refs)

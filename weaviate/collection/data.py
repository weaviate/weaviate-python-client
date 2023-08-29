import datetime
from typing import Dict, Any, Optional, List, Tuple, Union, Generic, Type, cast

import uuid as uuid_package
from google.protobuf.struct_pb2 import Struct
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes.data import (
    BatchReference,
    DataObject,
    Error,
    ReferenceTo,
    GetObjectByIdMetadata,
    GetObjectsMetadata,
    IncludesModel,
    ReferenceToMultiTarget,
    _BatchReturn,
)
from weaviate.collection.classes.internal import (
    _Object,
    _metadata_from_dict,
)
from weaviate.collection.classes.orm import (
    Model,
)
from weaviate.collection.config import _ConfigBase, _ConfigCollectionModel
from weaviate.collection.grpc_batch import _BatchGRPC
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.warnings import _Warnings
from weaviate.weaviate_types import BEACON, UUID
from weaviate_grpc import weaviate_pb2


class _Data:
    def __init__(
        self,
        connection: Connection,
        name: str,
        config: _ConfigBase,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ) -> None:
        self._connection = connection
        self.name = name
        self.__config = config
        self.__consistency_level = consistency_level
        self._tenant = tenant
        self._batch = _BatchGRPC(connection)

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

    def _insert_many(self, objects: List[DataObject]) -> _BatchReturn:
        weaviate_objs: List[weaviate_pb2.BatchObject] = [
            weaviate_pb2.BatchObject(
                class_name=self.name,
                vector=obj.vector if obj.vector is not None else None,
                uuid=str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4()),
                properties=self.__parse_properties_grpc(obj.data),
                tenant=self._tenant,
            )
            for obj in objects
        ]

        errors = self._batch.batch(weaviate_objs)

        all_responses: List[Union[uuid_package.UUID, Error]] = cast(
            List[Union[uuid_package.UUID, Error]], list(range(len(weaviate_objs)))
        )
        return_success: Dict[int, uuid_package.UUID] = {}
        return_errors: Dict[int, Error] = {}

        for idx, obj in enumerate(weaviate_objs):
            if idx in errors:
                error = Error(errors[idx], original_uuid=objects[idx].uuid)
                return_errors[idx] = error
                all_responses[idx] = error
            else:
                success = uuid_package.UUID(obj.uuid)
                return_success[idx] = success
                all_responses[idx] = success

        return _BatchReturn(
            uuids=return_success,
            errors=return_errors,
            has_errors=len(errors) > 0,
            all_responses=all_responses,
        )

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
        self, uuid: UUID, metadata: Optional[GetObjectByIdMetadata] = None
    ) -> Optional[Dict[str, Any]]:
        path = f"/objects/{self.name}/{uuid}"

        return self._get_from_weaviate(
            params=self.__apply_context({}), path=path, includes=metadata
        )

    def _get(self, metadata: Optional[GetObjectsMetadata] = None) -> Optional[Dict[str, Any]]:
        path = "/objects"
        params: Dict[str, Any] = {"class": self.name}

        return self._get_from_weaviate(
            params=self.__apply_context(params), path=path, includes=metadata
        )

    def _get_from_weaviate(
        self, params: Dict[str, Any], path: str, includes: Optional[IncludesModel] = None
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

    def _reference_add(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
        for beacon in ref.to_beacons():
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

    def _reference_add_many(self, refs: List[Dict[str, str]]) -> None:
        params: Dict[str, str] = {}
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level

        if self._tenant is not None:
            for ref in refs:
                ref["tenant"] = self._tenant

        response = self._connection.post(
            path="/batch/references", weaviate_object=refs, params=params
        )
        if response.status_code == 200:
            return None
        raise UnexpectedStatusCodeException("Send ref batch", response)

    def _reference_delete(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
        for beacon in ref.to_beacons():
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

    def _reference_replace(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self.name}/{from_uuid}/references/{from_property}"
        try:
            response = self._connection.put(
                path=path,
                weaviate_object=ref.to_beacons(),
                params=self.__apply_context(params),
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Reference was not added.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property reference to object", response)

    def __apply_context(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if self._tenant is not None:
            params["tenant"] = self._tenant
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level
        return params

    def __apply_context_to_params_and_object(
        self, params: Dict[str, Any], obj: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if self._tenant is not None:
            obj["tenant"] = self._tenant
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level
        return params, obj

    def _parse_properties(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: val.to_beacons() if isinstance(val, ReferenceTo) else self.__convert_primitive(val)
            for key, val in data.items()
        }

    def __convert_primitive(self, value: Any) -> Any:
        if isinstance(value, uuid_package.UUID):
            return str(value)
        if isinstance(value, datetime.datetime):
            if value.tzinfo is None:
                _Warnings.datetime_insertion_with_no_specified_timezone(value)
                value = value.replace(tzinfo=datetime.timezone.utc)
            return value.isoformat(sep="T", timespec="microseconds")
        if isinstance(value, list):
            return [self.__convert_primitive(val) for val in value]
        return value

    @staticmethod
    def __parse_properties_grpc(data: Dict[str, Any]) -> weaviate_pb2.BatchObject.Properties:
        multi_target: List[weaviate_pb2.BatchObject.RefPropertiesMultiTarget] = []
        single_target: List[weaviate_pb2.BatchObject.RefPropertiesSingleTarget] = []
        non_ref_properties: Struct = Struct()
        for key, val in data.items():
            if isinstance(val, ReferenceToMultiTarget):
                multi_target.append(
                    weaviate_pb2.BatchObject.RefPropertiesMultiTarget(
                        uuids=val.uuids_str, target_collection=val.target_collection, prop_name=key
                    )
                )
            elif isinstance(val, ReferenceTo):
                single_target.append(
                    weaviate_pb2.BatchObject.RefPropertiesSingleTarget(
                        uuids=val.uuids_str, prop_name=key
                    )
                )
            else:
                non_ref_properties.update({key: val})

        return weaviate_pb2.BatchObject.Properties(
            non_ref_properties=non_ref_properties,
            ref_props_multi=multi_target,
            ref_props_single=single_target,
        )


class _DataCollection(_Data):
    def _json_to_object(self, obj: Dict[str, Any]) -> _Object:
        return _Object(
            data={prop: val for prop, val in obj["properties"].items()},
            metadata=_metadata_from_dict(obj),
        )

    def insert(
        self,
        data: Dict[str, Any],
        uuid: Optional[UUID] = None,
        vector: Optional[List[float]] = None,
    ) -> uuid_package.UUID:
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._parse_properties(data),
            "id": str(uuid if uuid is not None else uuid_package.uuid4()),
        }

        if vector is not None:
            weaviate_obj["vector"] = vector

        return self._insert(weaviate_obj)

    def insert_many(self, objects: List[DataObject]) -> _BatchReturn:
        return self._insert_many(objects)

    def replace(
        self, data: Dict[str, Any], uuid: UUID, vector: Optional[List[float]] = None
    ) -> None:
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._parse_properties(data),
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._replace(weaviate_obj, uuid=uuid)

    def update(
        self, data: Dict[str, Any], uuid: UUID, vector: Optional[List[float]] = None
    ) -> None:
        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._parse_properties(data),
        }
        if vector is not None:
            weaviate_obj["vector"] = vector

        self._update(weaviate_obj, uuid=uuid)

    def get_by_id(
        self, uuid: UUID, metadata: Optional[GetObjectByIdMetadata] = None
    ) -> Optional[_Object]:
        ret = self._get_by_id(uuid=uuid, metadata=metadata)
        if ret is None:
            return ret
        return self._json_to_object(ret)

    def get(self, metadata: Optional[GetObjectsMetadata] = None) -> List[_Object]:
        ret = self._get(metadata=metadata)
        if ret is None:
            return []

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        self._reference_add(
            from_uuid=from_uuid,
            from_property=from_property,
            ref=ref,
        )

    def reference_add_many(self, from_property: str, refs: List[BatchReference]) -> None:
        refs_dict = [
            {
                "from": BEACON + f"{self.name}/{ref.from_uuid}/{from_property}",
                "to": BEACON + str(ref.to_uuid),
            }
            for ref in refs
        ]
        self._reference_add_many(refs_dict)

    def reference_delete(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_replace(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)


class _DataCollectionModel(Generic[Model], _Data):
    def __init__(
        self,
        connection: Connection,
        name: str,
        model: Type[Model],
        config: _ConfigCollectionModel,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        super().__init__(connection, name, config, consistency_level, tenant)
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
            data=self.__model.model_validate(
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
            "properties": self._parse_properties(obj.props_to_dict()),
            "id": str(obj.uuid),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._insert(weaviate_obj)
        return uuid_package.UUID(str(obj.uuid))

    def insert_many(self, objects: List[Model]) -> _BatchReturn:
        for obj in objects:
            self.__model.model_validate(obj)

        data_objects = [
            DataObject(
                data=obj.props_to_dict(),
                uuid=obj.uuid,
                vector=obj.vector,
            )
            for obj in objects
        ]

        return self._insert_many(data_objects)

    def replace(self, obj: Model, uuid: UUID) -> None:
        self.__model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._parse_properties(obj.props_to_dict()),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._replace(weaviate_obj, uuid)

    def update(self, obj: Model, uuid: UUID) -> None:
        self.__model.model_validate(obj)

        weaviate_obj: Dict[str, Any] = {
            "class": self.name,
            "properties": self._parse_properties(obj.props_to_dict()),
        }
        if obj.vector is not None:
            weaviate_obj["vector"] = obj.vector

        self._update(weaviate_obj, uuid)

    def get_by_id(
        self, uuid: UUID, metadata: Optional[GetObjectByIdMetadata] = None
    ) -> Optional[_Object[Model]]:
        ret = self._get_by_id(uuid=uuid, includes=metadata)
        if ret is None:
            return None
        return self._json_to_object(ret)

    def get(self, metadata: Optional[GetObjectsMetadata] = None) -> List[_Object[Model]]:
        ret = self._get(includes=metadata)
        if ret is None:
            return []

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        self._reference_add(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_delete(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        self._reference_delete(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_replace(self, from_uuid: UUID, from_property: str, ref: ReferenceTo) -> None:
        self._reference_replace(from_uuid=from_uuid, from_property=from_property, ref=ref)

    def reference_add_many(self, from_property: str, refs: List[BatchReference]) -> None:
        refs_dict = [
            {
                "from": BEACON + f"{self.name}/{ref.from_uuid}/{from_property}",
                "to": BEACON + str(ref.to_uuid),
            }
            for ref in refs
        ]
        self._reference_add_many(refs_dict)

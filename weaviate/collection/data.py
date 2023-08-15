from typing import Dict, Any, Optional, List, Tuple, Union, Generic, Type

import uuid as uuid_package
from google.protobuf.struct_pb2 import Struct
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes import (
    BatchReference,
    DataObject,
    Error,
    Errors,
    ReferenceTo,
    GetObjectByIdIncludes,
    GetObjectsIncludes,
    IncludesModel,
    _metadata_from_dict,
    _Object,
    UUID,
    Model,
    ReferenceToMultiTarget,
)
from weaviate.collection.config import _ConfigBase, _ConfigCollectionModel
from weaviate.collection.grpc_batch import _BatchGRPC
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.weaviate_types import BEACON, UUIDS
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

    def _insert_many(self, objects: List[Dict[str, Any]]) -> List[Union[uuid_package.UUID, Errors]]:
        params: Dict[str, str] = {}
        if self.__consistency_level is not None:
            params["consistency_level"] = self.__consistency_level

        if self._tenant is not None:
            for obj in objects:
                obj["tenant"] = self._tenant

        response = self._connection.post(
            path="/batch/objects",
            weaviate_object={"fields": ["ALL"], "objects": objects},
            params=params,
        )
        if response.status_code == 200:
            results = response.json()
            return [
                [Error(message=err) for err in result["result"]["errors"]["error"]]
                if "result" in result
                and "errors" in result["result"]
                and "error" in result["result"]["errors"]
                else objects[i]["id"]
                for i, result in enumerate(results)
            ]

        raise UnexpectedStatusCodeException("Send object batch", response)

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
        self, uuid: UUID, includes: Optional[GetObjectByIdIncludes] = None
    ) -> Optional[Dict[str, Any]]:
        path = f"/objects/{self.name}/{uuid}"

        return self._get_from_weaviate(
            params=self.__apply_context({}), path=path, includes=includes
        )

    def _get(self, includes: Optional[GetObjectsIncludes] = None) -> Optional[Dict[str, Any]]:
        path = "/objects"
        params: Dict[str, Any] = {"class": self.name}

        return self._get_from_weaviate(
            params=self.__apply_context(params), path=path, includes=includes
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
        beacons = ref.to_beacons()
        for beacon in beacons:
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
        beacons = ref.to_beacons()
        for beacon in beacons:
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
        beacons = ref.to_beacons()
        try:
            response = self._connection.put(
                path=path,
                weaviate_object=beacons,
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
            key: val if not isinstance(val, ReferenceTo) else val.to_beacons()
            for key, val in data.items()
        }

    def _parse_properties_grpc(self, data: Dict[str, Any]) -> weaviate_pb2.Properties:
        multi_target: List[weaviate_pb2.BatchObject.RefPropertiesMultiTarget] = []
        single_target: List[weaviate_pb2.BatchObject.RefPropertiesSingleTarget] = []
        non_ref_properties: Struct = Struct()
        for key, val in data.items():
            if isinstance(val, ReferenceToMultiTarget):
                multi_target.append(
                    weaviate_pb2.BatchObject.RefPropertiesMultiTarget(
                        uuids=val.uuids, target_collection=val.target_collection, prop_name=key
                    )
                )
            elif isinstance(val, ReferenceTo):
                single_target.append(
                    weaviate_pb2.BatchObject.RefPropertiesSingleTarget(
                        uuids=val.uuids, prop_name=key
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

    def insert_many(self, objects: List[DataObject]) -> List[Union[uuid_package.UUID, Errors]]:
        weaviate_objs: List[weaviate_pb2.BatchObject] = [
            weaviate_pb2.BatchObject(
                class_name=self.name,
                vector=obj.vector if obj.vector is not None else None,
                uuid=str(obj.uuid) if obj.uuid is not None else str(uuid_package.uuid4()),
                properties=self._parse_properties_grpc(obj.data),
                tenant=self._tenant,
            )
            for obj in objects
        ]

        self._batch.batch(weaviate_objs)

        return [obj.uuid for obj in weaviate_objs]

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
        self, uuid: UUID, includes: Optional[GetObjectByIdIncludes] = None
    ) -> Optional[_Object]:
        ret = self._get_by_id(uuid=uuid, includes=includes)
        if ret is None:
            return ret
        return self._json_to_object(ret)

    def get(self, includes: Optional[GetObjectsIncludes] = None) -> List[_Object]:
        ret = self._get(includes=includes)
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

        model_object = _Object[Model](
            data=self.__model(**obj["properties"]), metadata=_metadata_from_dict(obj)
        )
        model_object.data.uuid = model_object.metadata.uuid
        model_object.data.vector = model_object.metadata.vector
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

    def insert_many(self, objects: List[Model]) -> List[Union[uuid_package.UUID, Errors]]:
        for obj in objects:
            self.__model.model_validate(obj)

        weaviate_objs: List[Dict[str, Any]] = [
            {
                "class": self.name,
                "properties": self._parse_properties(obj.props_to_dict()),
                "id": str(obj.uuid),
            }
            for obj in objects
        ]
        return self._insert_many(weaviate_objs)

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
        self, uuid: UUID, includes: Optional[GetObjectByIdIncludes] = None
    ) -> Optional[_Object[Model]]:
        ret = self._get_by_id(uuid=uuid, includes=includes)
        if ret is None:
            return None
        return self._json_to_object(ret)

    def get(self, includes: Optional[GetObjectsIncludes] = None) -> Optional[List[_Object[Model]]]:
        ret = self._get(includes=includes)
        if ret is None:
            return None

        return [self._json_to_object(obj) for obj in ret["objects"]]

    def reference_add(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_add(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_delete(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_delete(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
        )

    def reference_replace(self, from_uuid: UUID, from_property: str, to_uuids: UUIDS) -> None:
        self._reference_replace(
            from_uuid=from_uuid, from_property_name=from_property, to_uuids=to_uuids
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

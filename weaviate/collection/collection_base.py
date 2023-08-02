from copy import copy
from typing import Dict, Any, Optional, List, Tuple, Union

import uuid as uuid_package
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.collection_classes import Errors, Error
from weaviate.connect import Connection
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.util import _to_beacons
from weaviate.weaviate_classes import CollectionConfigBase, UUID, Metadata
from weaviate.weaviate_types import UUIDS


class CollectionObjectBase:
    def __init__(self, connection: Connection, name: str) -> None:
        self._connection = connection
        self._name = name
        self._tenant: Optional[str] = None
        self._consistency_level: Optional[str] = None

    def _with_tenant(self, tenant: Optional[str] = None) -> "CollectionObjectBase":
        new = copy(self)
        new._tenant = tenant
        return new

    def _with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObjectBase":
        new = copy(self)
        new._consistency_level = (
            ConsistencyLevel(consistency_level).value if consistency_level is not None else None
        )
        return new

    def _insert(self, weaviate_obj: Dict[str, Any]) -> uuid_package.UUID:
        path = "/objects"
        try:
            response = self._connection.post(
                path=path, weaviate_object=weaviate_obj, params=self.__apply_context({})
            )
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
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level

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
        path = f"/objects/{self._name}/{uuid}"

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
        path = f"/objects/{self._name}/{uuid}"
        params, weaviate_obj = self.__apply_context_to_params_and_object({}, weaviate_obj)

        try:
            response = self._connection.put(path=path, weaviate_object=weaviate_obj, params=params)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Object was not replaced.") from conn_err
        if response.status_code == 200:
            return
        raise UnexpectedStatusCodeException("Replacing object", response)

    def _update(self, weaviate_obj: Dict[str, Any], uuid: UUID) -> None:
        path = f"/objects/{self._name}/{uuid}"
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
        self, uuid: UUID, metadata: Optional[Metadata] = None
    ) -> Optional[Dict[str, Any]]:
        path = f"/objects/{self._name}/{uuid}"

        return self._get_from_weaviate(
            params=self.__apply_context({}), path=path, metadata=metadata
        )

    def _get(self, metadata: Optional[Metadata] = None) -> Optional[Dict[str, Any]]:
        path = "/objects"
        params: Dict[str, Any] = {"class": self._name}

        return self._get_from_weaviate(
            params=self.__apply_context(params), path=path, metadata=metadata
        )

    def _get_from_weaviate(
        self, params: Dict[str, Any], path: str, metadata: Optional[Metadata] = None
    ) -> Optional[Dict[str, Any]]:
        include = ""
        if metadata is not None:
            include += metadata.to_rest()

        if len(include) > 0:
            params["include"] = include

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

    def _reference_add(self, from_uuid: str, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self._name}/{from_uuid}/references/{from_property_name}"
        beacons = _to_beacons(to_uuids)
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

    def _reference_batch_add(self, refs: List[Dict[str, str]]):
        params: Dict[str, str] = {}
        if self._consistency_level is not None:
            params["consistency_level"] = self._consistency_level

        if self._tenant is not None:
            for ref in refs:
                ref["tenant"] = self._tenant

        response = self._connection.post(
            path="/batch/references", weaviate_object=refs, params=params
        )
        if response.status_code == 200:
            return response
        raise UnexpectedStatusCodeException("Send ref batch", response)

    def _reference_delete(self, from_uuid: str, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self._name}/{from_uuid}/references/{from_property_name}"
        beacons = _to_beacons(to_uuids)
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

    def _reference_replace(self, from_uuid: UUID, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self._name}/{from_uuid}/references/{from_property_name}"
        try:
            response = self._connection.put(
                path=path,
                weaviate_object=_to_beacons(to_uuids),
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


class CollectionBase:
    def __init__(self, connection: Connection):
        self._connection = connection

    def _create(
        self,
        model: CollectionConfigBase,
        properties: Optional[List[Dict[str, Any]]] = None,
        name: Optional[str] = None,
    ) -> str:
        weaviate_object = model.to_dict()
        if properties is not None:
            weaviate_object["properties"] = properties
        if name is not None:
            weaviate_object["class"] = name

        try:
            response = self._connection.post(path="/schema", weaviate_object=weaviate_object)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

        collection_name = response.json()["class"]
        assert isinstance(collection_name, str)
        return collection_name

    def _exists(self, name: str) -> bool:
        path = f"/schema/{_capitalize_names(name)}"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Existenz of class.") from conn_err
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False

        UnexpectedStatusCodeException("collection exists", response)

    def _delete(self, name: str) -> None:
        path = f"/schema/{_capitalize_names(name)}"
        try:
            response = self._connection.delete(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Deletion of class.") from conn_err
        if response.status_code == 200:
            return

        UnexpectedStatusCodeException("Delete collection", response)


def _capitalize_names(name: str) -> str:
    collection_name = name[0].upper()
    if len(name) > 1:
        collection_name += name[1:]
    return collection_name

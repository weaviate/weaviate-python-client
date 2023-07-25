import uuid as uuid_package
from typing import Dict, Any, Optional, List

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.util import _to_beacons
from weaviate.weaviate_classes import CollectionConfigBase, UUID, Metadata
from weaviate.weaviate_types import UUIDS


class CollectionObjectBase:
    def __init__(self, connection: Connection, name: str) -> None:
        self._connection = connection
        self._name = name

    def _insert(self, weaviate_obj: Dict[str, Any]) -> uuid_package.UUID:
        path = "/objects"
        try:
            response = self._connection.post(path=path, weaviate_object=weaviate_obj, params={})
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

    def _get_by_id(
        self, uuid: UUID, metadata: Optional[Metadata] = None
    ) -> Optional[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        path = f"/objects/{self._name}/{uuid}"

        return self._get_from_weaviate(params=params, path=path, metadata=metadata)

    def _get(self, metadata: Optional[Metadata] = None) -> Optional[Dict[str, Any]]:
        path = "/objects"
        params: Dict[str, Any] = {"class": self._name}

        return self._get_from_weaviate(params=params, path=path, metadata=metadata)

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
                    params=params,
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError("Reference was not added.") from conn_err
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Add property reference to object", response)

    def _reference_delete(self, from_uuid: str, from_property_name: str, to_uuids: UUIDS) -> None:
        params: Dict[str, str] = {}

        path = f"/objects/{self._name}/{from_uuid}/references/{from_property_name}"
        beacons = _to_beacons(to_uuids)
        for beacon in beacons:
            try:
                response = self._connection.delete(
                    path=path,
                    weaviate_object=beacon,
                    params=params,
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
                params=params,
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Reference was not added.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property reference to object", response)


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
            weaviate_object["class"] = name.capitalize()

        try:
            response = self._connection.post(path="/schema", weaviate_object=weaviate_object)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

        collection_name = response.json()["class"]
        assert isinstance(collection_name, str)
        return collection_name

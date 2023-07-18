import uuid as uuid_package
from typing import Dict, Any, Optional

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException, ObjectAlreadyExistsException
from weaviate.weaviate_types import CollectionConfigBase, UUID, Metadata


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


class CollectionBase:
    def __init__(self, connection: Connection):
        self._connection = connection

    def _create(self, model: CollectionConfigBase) -> None:
        try:
            response = self._connection.post(path="/schema", weaviate_object=model.to_dict())
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

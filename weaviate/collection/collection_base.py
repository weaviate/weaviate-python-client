from typing import Dict

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes.config import (
    CollectionConfigCreateBase,
    _collection_configs_from_json,
    _CollectionConfig,
)
from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException


class CollectionBase:
    def __init__(self, connection: Connection):
        self._connection = connection

    def _create(
        self,
        config: CollectionConfigCreateBase,
    ) -> str:
        weaviate_object = config.to_dict()

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
        path = f"/schema/{name}"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Existenz of class.") from conn_err

        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False
        raise UnexpectedStatusCodeException("collection exists", response)

    def _delete(self, name: str) -> None:
        path = f"/schema/{name}"
        try:
            response = self._connection.delete(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Deletion of class.") from conn_err
        if response.status_code == 200:
            return

        UnexpectedStatusCodeException("Delete collection", response)

    def get_all_collection_configs(self) -> Dict[str, _CollectionConfig]:
        try:
            response = self._connection.get(path="/schema")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema.") from conn_err
        if response.status_code == 200:
            res = response.json()
            return _collection_configs_from_json(res)
        raise UnexpectedStatusCodeException("Get schema", response)

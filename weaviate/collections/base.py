from typing import Dict

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.collections.classes.config import (
    _CollectionConfigCreateBase,
    _CollectionConfig,
    _CollectionConfigSimple,
)
from weaviate.collections.classes.config_methods import (
    _collection_configs_from_json,
    _collection_configs_simple_from_json,
)
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _capitalize_first_letter


class _CollectionBase:
    def __init__(self, name: str) -> None:
        self.name = _capitalize_first_letter(name)


class _CollectionsBase:
    def __init__(self, connection: Connection):
        self._connection = connection

    def _create(
        self,
        config: _CollectionConfigCreateBase,
    ) -> str:
        weaviate_object = config._to_dict()

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

    def _get_all(self) -> Dict[str, _CollectionConfig]:
        try:
            response = self._connection.get(path="/schema")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema.") from conn_err
        if response.status_code == 200:
            res = response.json()
            return _collection_configs_from_json(res)
        raise UnexpectedStatusCodeException("Get schema", response)

    def _get_simple(self) -> Dict[str, _CollectionConfigSimple]:
        try:
            response = self._connection.get(path="/schema")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema.") from conn_err
        if response.status_code == 200:
            res = response.json()
            return _collection_configs_simple_from_json(res)
        raise UnexpectedStatusCodeException("Get schema", response)

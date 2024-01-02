from typing import Dict, List, TYPE_CHECKING

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.collections.classes.cluster import Shard
from weaviate.collections.classes.config import (
    _CollectionConfig,
    _CollectionConfigSimple,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_configs_from_json,
    _collection_configs_simple_from_json,
)
from weaviate.collections.cluster import _Cluster
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict

if TYPE_CHECKING:
    from weaviate.collections.batch.executor import BatchExecutor


class _CollectionBase:
    def __init__(self, connection: Connection, name: str) -> None:
        self._connection = connection
        self.name = _capitalize_first_letter(name)
        self.__cluster = _Cluster(connection)

    def shards(self) -> List[Shard]:
        """
        Get the statuses of all the shards of this collection.

        Returns:
            The list of shards belonging to this collection.

        Raises
            `requests.ConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If weaviate reports a none OK status.
            `weaviate.EmptyResponseException`
                If the response is empty.
        """
        shards: List[Shard] = []
        for node in self.__cluster.nodes(self.name, output="verbose"):
            shards.extend(node.shards)
        return shards


class _CollectionsBase:
    def __init__(self, connection: Connection, batch_executor: "BatchExecutor"):
        self._batch_executor = batch_executor
        self._connection = connection

    def _create(
        self,
        config: dict,
    ) -> str:
        try:
            response = self._connection.post(path="/schema", weaviate_object=config)
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

    def _export(self, name: str) -> _CollectionConfig:
        path = f"/schema/{name}"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema export.") from conn_err
        res = _decode_json_response_dict(response, "Get schema export")
        assert res is not None
        return _collection_config_from_json(res)

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
        res = _decode_json_response_dict(response, "Get schema all")
        assert res is not None
        return _collection_configs_from_json(res)

    def _get_simple(self) -> Dict[str, _CollectionConfigSimple]:
        try:
            response = self._connection.get(path="/schema")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Get schema.") from conn_err
        res = _decode_json_response_dict(response, "Get schema simple")
        assert res is not None
        return _collection_configs_simple_from_json(res)

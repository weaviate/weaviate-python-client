from typing import Dict, List, Union


from weaviate.collections.classes.cluster import Shard
from weaviate.collections.classes.config import (
    _CollectionConfig,
    CollectionConfig,
    CollectionConfigSimple,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_configs_from_json,
    _collection_configs_simple_from_json,
)
from weaviate.collections.cluster import _Cluster
from weaviate.connect import ConnectionV4
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict

from weaviate.connect.v4 import _ExpectedStatusCodes


class _CollectionBase:
    def __init__(self, connection: ConnectionV4, name: str, validate_arguments: bool) -> None:
        self._connection = connection
        self.name = _capitalize_first_letter(name)
        self.__cluster = _Cluster(connection)
        self._validate_arguments = validate_arguments

    def shards(self) -> List[Shard]:
        """
        Get the statuses of all the shards of this collection.

        Returns:
            The list of shards belonging to this collection.

        Raises
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If weaviate reports a none OK status.
            `weaviate.EmptyResponseError`
                If the response is empty.
        """
        return [
            shard
            for node in self.__cluster.nodes(self.name, output="verbose")
            for shard in node.shards
        ]


class _CollectionsBase:
    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    def _create(
        self,
        config: dict,
    ) -> str:
        response = self._connection.post(
            path="/schema",
            weaviate_object=config,
            error_msg="Collection may not have been created properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Create collection"),
        )

        collection_name = response.json()["class"]
        assert isinstance(collection_name, str)
        return collection_name

    def _exists(self, name: str) -> bool:
        path = f"/schema/{name}"
        response = self._connection.get(
            path=path,
            error_msg="Collection may not exist.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="collection exists"),
        )

        if response.status_code == 200:
            return True
        else:
            assert response.status_code == 404
            return False

    def _export(self, name: str) -> _CollectionConfig:
        path = f"/schema/{name}"
        response = self._connection.get(path=path, error_msg="Could not export collection config")
        res = _decode_json_response_dict(response, "Get schema export")
        assert res is not None
        return _collection_config_from_json(res)

    def _delete(self, name: str) -> None:
        path = f"/schema/{name}"
        self._connection.delete(
            path=path,
            error_msg="Collection may not have been deleted properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Delete collection"),
        )

    def _get_all(
        self, simple: bool
    ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]:
        response = self._connection.get(path="/schema", error_msg="Get all collections")
        res = _decode_json_response_dict(response, "Get schema all")
        assert res is not None
        if simple:
            return _collection_configs_simple_from_json(res)
        return _collection_configs_from_json(res)

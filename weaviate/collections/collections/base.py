from typing import Dict, Union

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
from weaviate.connect import ConnectionV4
from weaviate.util import _decode_json_response_dict

from weaviate.connect.v4 import _ExpectedStatusCodes


class _CollectionsBase:
    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    async def _create(
        self,
        config: dict,
    ) -> str:
        response = await self._connection.post(
            path="/schema",
            weaviate_object=config,
            error_msg="Collection may not have been created properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Create collection"),
        )

        collection_name = response.json()["class"]
        assert isinstance(collection_name, str)
        return collection_name

    async def _exists(self, name: str) -> bool:
        path = f"/schema/{name}"
        response = await self._connection.get(
            path=path,
            error_msg="Collection may not exist.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="collection exists"),
        )

        if response.status_code == 200:
            return True
        else:
            assert response.status_code == 404
            return False

    async def _export(self, name: str) -> _CollectionConfig:
        path = f"/schema/{name}"
        response = await self._connection.get(
            path=path, error_msg="Could not export collection config"
        )
        res = _decode_json_response_dict(response, "Get schema export")
        assert res is not None
        return _collection_config_from_json(res)

    async def _delete(self, name: str) -> None:
        path = f"/schema/{name}"
        await self._connection.delete(
            path=path,
            error_msg="Collection may not have been deleted properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Delete collection"),
        )

    async def _get_all(
        self, simple: bool
    ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]:
        response = await self._connection.get(path="/schema", error_msg="Get all collections")
        res = _decode_json_response_dict(response, "Get schema all")
        assert res is not None
        if simple:
            return _collection_configs_simple_from_json(res)
        return _collection_configs_from_json(res)

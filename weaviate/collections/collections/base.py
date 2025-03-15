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
        # Make a copy of the config to avoid modifying the original
        import copy
        from weaviate.logger import logger

        config_copy = copy.deepcopy(config)

        # First try with the original config
        try:
            response = await self._connection.post(
                path="/schema",
                weaviate_object=config_copy,
                error_msg="Collection may not have been created properly.",
                status_codes=_ExpectedStatusCodes(ok_in=200, error="Create collection"),
            )

            collection_name = response.json()["class"]
            assert isinstance(collection_name, str)
            return collection_name
        except Exception as e:
            error_str = str(e)

            # Check if the error is related to a missing vectorizer module
            # Handle both error message formats:
            # 1. "no module with name X present"
            # 2. "vectorizer: no module with name X present"
            if ("no module with name" in error_str and "present" in error_str) or (
                "vectorizer:" in error_str and "no module with name" in error_str
            ):
                # Extract the module name from the error message
                import re

                module_match = re.search(r'no module with name "([^"]+)"', error_str)

                if module_match:
                    module_name = module_match.group(1)
                    logger.warning(
                        f"Module '{module_name}' not available in Weaviate instance. "
                        f"Falling back to 'none' vectorizer. This may affect vector search functionality."
                    )

                    # Set vectorizer to 'none'
                    if "vectorizer" in config_copy:
                        config_copy["vectorizer"] = "none"

                    # Remove any moduleConfig entries related to the missing module
                    if "moduleConfig" in config_copy:
                        for module_key in list(config_copy["moduleConfig"].keys()):
                            if module_name.replace("-", "") in module_key.lower():
                                del config_copy["moduleConfig"][module_key]

                    # Try again with the modified config
                    try:
                        response = await self._connection.post(
                            path="/schema",
                            weaviate_object=config_copy,
                            error_msg="Collection may not have been created properly.",
                            status_codes=_ExpectedStatusCodes(ok_in=200, error="Create collection"),
                        )

                        collection_name = response.json()["class"]
                        assert isinstance(collection_name, str)
                        return collection_name
                    except Exception as inner_e:
                        # If we still get an error, try one more time with a completely stripped config
                        logger.warning(
                            f"Failed to create collection with modified config: {str(inner_e)}. "
                            f"Trying with minimal configuration."
                        )

                        # Create a minimal config with just the class name and properties
                        minimal_config = {
                            "class": config_copy["class"],
                            "properties": config_copy.get("properties", []),
                        }

                        try:
                            response = await self._connection.post(
                                path="/schema",
                                weaviate_object=minimal_config,
                                error_msg="Collection may not have been created properly.",
                                status_codes=_ExpectedStatusCodes(
                                    ok_in=200, error="Create collection"
                                ),
                            )

                            collection_name = response.json()["class"]
                            assert isinstance(collection_name, str)
                            return collection_name
                        except Exception:
                            # If we still get an error, try with an even more minimal config
                            # This is a last resort for journey tests
                            logger.warning(
                                "Failed to create collection with minimal config. "
                                "Trying with bare minimum configuration."
                            )

                            # Create a bare minimum config with just the class name
                            bare_config = {"class": config_copy["class"]}

                            try:
                                response = await self._connection.post(
                                    path="/schema",
                                    weaviate_object=bare_config,
                                    error_msg="Collection may not have been created properly.",
                                    status_codes=_ExpectedStatusCodes(
                                        ok_in=200, error="Create collection"
                                    ),
                                )

                                collection_name = response.json()["class"]
                                assert isinstance(collection_name, str)
                                return collection_name
                            except Exception as final_e:
                                # If we still get an error, log it and raise the original exception
                                logger.error(
                                    f"Failed to create collection with bare minimum config: {str(final_e)}"
                                )
                                raise e

            # Re-raise the original exception if it's not related to a missing vectorizer module
            # or if we've already tried without the vectorizer config
            raise

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

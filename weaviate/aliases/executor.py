from typing import Dict, Generic, List, Optional, cast

from httpx import Response

from weaviate.aliases.alias import AliasReturn, _WeaviateAlias
from weaviate.connect import executor
from weaviate.connect.v4 import Connection, ConnectionType, _ExpectedStatusCodes
from weaviate.util import _decode_json_response_dict


class _AliasExecutor(Generic[ConnectionType]):
    def __init__(self, connection: Connection):
        self._connection = connection

    def list_all(
        self, *, collection: Optional[str] = None
    ) -> executor.Result[Dict[str, AliasReturn]]:
        """Get the alias for a given alias name."""
        self._connection._weaviate_version.check_is_at_least_1_32_0("alias")

        error_msg = "list all aliases"
        if collection is not None:
            error_msg += f" for collection {collection}"

        def resp(res: Response) -> Dict[str, AliasReturn]:
            response_typed = _decode_json_response_dict(res, "list all aliases")
            assert response_typed is not None
            aliases = response_typed.get("aliases")
            assert aliases is not None, "Expected 'aliases' in response"
            return {
                alias["alias"]: AliasReturn(alias=alias["alias"], collection=alias["class"])
                for alias in cast(List[_WeaviateAlias], aliases)
            }

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/aliases",
            error_msg=error_msg,
            params={"class": collection} if collection else None,
            status_codes=_ExpectedStatusCodes(
                ok_in=[200],
                error=error_msg,
            ),
        )

    def get(self, *, alias_name: str) -> executor.Result[Optional[AliasReturn]]:
        """Get the given alias."""
        self._connection._weaviate_version.check_is_at_least_1_32_0("alias")

        def resp(res: Response) -> Optional[AliasReturn]:
            if res.status_code == 404:
                return None
            response_typed = _decode_json_response_dict(res, "get alias")
            assert response_typed is not None

            return AliasReturn(alias=response_typed["alias"], collection=response_typed["class"])

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/aliases/{alias_name}",
            error_msg=f"Could not get alias {alias_name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404],
                error="get alias",
            ),
        )

    def create(self, *, alias_name: str, target_collection: str) -> executor.Result[None]:
        """Create an alias for a given collection."""
        self._connection._weaviate_version.check_is_at_least_1_32_0("alias")

        def resp(res: Response) -> None:
            return None

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path="/aliases",
            error_msg=f"Could not create alias {alias_name} for collection {target_collection}",
            weaviate_object={"class": target_collection, "alias": alias_name},
            status_codes=_ExpectedStatusCodes(
                ok_in=[200],
                error="create aliases",
            ),
        )

    def delete(self, *, alias_name: str) -> executor.Result[bool]:
        """Create an alias."""
        self._connection._weaviate_version.check_is_at_least_1_32_0("alias")

        def resp(res: Response) -> bool:
            return res.status_code == 204

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=f"/aliases/{alias_name}",
            error_msg=f"Could not delete alias {alias_name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[204, 404],
                error="delete aliases",
            ),
        )

    def update(self, *, alias_name: str, new_target_collection: str) -> executor.Result[bool]:
        """Replace an alias."""
        self._connection._weaviate_version.check_is_at_least_1_32_0("alias")

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.put,
            path=f"/aliases/{alias_name}",
            weaviate_object={"class": new_target_collection},
            error_msg=f"Could not update alias {alias_name} to point to collection {new_target_collection}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404],
                error="update aliases",
            ),
        )

    def exists(self, *, alias_name: str) -> executor.Result[bool]:
        """Use this method to check if an alias exists in the Weaviate instance.

        Args:
            name: The name of the alias to check.

        Returns:
            `True` if the alias exists, `False` otherwise.
        """
        self._connection._weaviate_version.check_is_at_least_1_32_0("alias")

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/aliases/{alias_name}",
            error_msg="Alias may not exist.",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="alias exists"),
        )

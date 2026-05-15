from typing import Generic, List, Optional

from httpx import Response

from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.namespaces.models import Namespace
from weaviate.util import _decode_json_response_dict, _decode_json_response_list


class _NamespacesExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def create(self, *, name: str) -> executor.Result[Namespace]:
        """Create a new namespace.

        Args:
            name: The namespace name. Must be 3-36 lowercase alphanumeric characters starting with a letter.

        Returns:
            The created Namespace.
        """
        self._connection._weaviate_version.check_is_at_least_1_38_0("namespaces")

        def resp(res: Response) -> Namespace:
            parsed = _decode_json_response_dict(res, "Create namespace")
            assert parsed is not None
            return Namespace(name=parsed["name"])

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/namespaces/{name}",
            weaviate_object={},
            error_msg=f"Could not create namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create namespace"),
        )

    def get(self, *, name: str) -> executor.Result[Optional[Namespace]]:
        """Get a namespace by name.

        Args:
            name: The name of the namespace to retrieve.

        Returns:
            The Namespace, or None if it does not exist.
        """
        self._connection._weaviate_version.check_is_at_least_1_38_0("namespaces")

        def resp(res: Response) -> Optional[Namespace]:
            if res.status_code == 404:
                return None
            parsed = _decode_json_response_dict(res, "Get namespace")
            assert parsed is not None
            return Namespace(name=parsed["name"])

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/namespaces/{name}",
            error_msg=f"Could not get namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get namespace"),
        )

    def list_all(self) -> executor.Result[List[Namespace]]:
        """List all namespaces visible to the current principal.

        Returns:
            A list of Namespace objects.
        """
        self._connection._weaviate_version.check_is_at_least_1_38_0("namespaces")

        def resp(res: Response) -> List[Namespace]:
            parsed = _decode_json_response_list(res, "List namespaces")
            return [Namespace(name=ns["name"]) for ns in (parsed or [])]

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/namespaces",
            error_msg="Could not list namespaces",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="List namespaces"),
        )

    def delete(self, *, name: str) -> executor.Result[None]:
        """Delete a namespace.

        The server marks the namespace for deletion and cleans up its classes,
        aliases, and users asynchronously, so this call returns as soon as the
        deletion has been accepted (HTTP 202), not when cleanup has finished.

        Args:
            name: The name of the namespace to delete.
        """
        self._connection._weaviate_version.check_is_at_least_1_38_0("namespaces")

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=f"/namespaces/{name}",
            error_msg=f"Could not delete namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[202], error="Delete namespace"),
        )

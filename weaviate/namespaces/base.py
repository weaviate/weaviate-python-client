from typing import Any, Dict, Generic, List, Optional, cast

from httpx import Response

from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.namespaces.models import Namespace, NamespaceState
from weaviate.util import _decode_json_response_dict, _decode_json_response_list


class _NamespacesExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    @staticmethod
    def _ns_from_dict(data: Dict[str, Any]) -> Namespace:
        return Namespace(
            name=data["name"],
            home_nodes=data.get("home_nodes") or [],
            state=cast(Optional[NamespaceState], data.get("state")),
        )

    def create(
        self, *, name: str, home_nodes: Optional[List[str]] = None
    ) -> executor.Result[Namespace]:
        """Create a new namespace.

        Args:
            name: The namespace name. Must be 3-36 lowercase alphanumeric characters starting with a letter.
            home_nodes: The cluster nodes to place this namespace's shards on, in placement order. Each
                must be a current storage candidate. When omitted, the cluster picks them automatically.

        Returns:
            The created Namespace.
        """
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> Namespace:
            parsed = _decode_json_response_dict(res, "Create namespace")
            assert parsed is not None
            return self._ns_from_dict(parsed)

        body: Dict[str, Any] = {}
        if home_nodes is not None:
            body["home_nodes"] = home_nodes

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/namespaces/{name}",
            weaviate_object=body,
            error_msg=f"Could not create namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create namespace"),
        )

    def update(self, *, name: str, home_nodes: List[str]) -> executor.Result[Namespace]:
        """Update the home nodes of an existing namespace.

        Changing the home nodes only affects future placement decisions; existing live shards
        are not moved.

        Args:
            name: The name of the namespace to update.
            home_nodes: The cluster nodes to use for future placements, in placement order. Must not be
                empty, and each must be a current storage candidate.

        Returns:
            The updated Namespace.
        """
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> Namespace:
            parsed = _decode_json_response_dict(res, "Update namespace")
            assert parsed is not None
            return self._ns_from_dict(parsed)

        return executor.execute(
            response_callback=resp,
            method=self._connection.put,
            path=f"/namespaces/{name}",
            weaviate_object={"home_nodes": home_nodes},
            error_msg=f"Could not update namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Update namespace"),
        )

    def get(self, *, name: str) -> executor.Result[Optional[Namespace]]:
        """Get a namespace by name.

        Args:
            name: The name of the namespace to retrieve.

        Returns:
            The Namespace, or None if it does not exist.
        """
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> Optional[Namespace]:
            if res.status_code == 404:
                return None
            parsed = _decode_json_response_dict(res, "Get namespace")
            assert parsed is not None
            return self._ns_from_dict(parsed)

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
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> List[Namespace]:
            parsed = _decode_json_response_list(res, "List namespaces")
            return [self._ns_from_dict(ns) for ns in (parsed or [])]

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
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=f"/namespaces/{name}",
            error_msg=f"Could not delete namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[202], error="Delete namespace"),
        )

    def suspend(self, *, name: str) -> executor.Result[None]:
        """Suspend a namespace.

        Its users can no longer authenticate and it accepts no new resources. Everything it
        owns is kept. Suspending an already suspended namespace is a no-op.

        Args:
            name: The name of the namespace to suspend.
        """
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/namespaces/{name}/suspend",
            weaviate_object={},
            error_msg=f"Could not suspend namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[202], error="Suspend namespace"),
        )

    def resume(self, *, name: str) -> executor.Result[None]:
        """Return a suspended namespace to the active state.

        Resuming an already active namespace is a no-op.

        Args:
            name: The name of the namespace to resume.
        """
        self._connection._weaviate_version.check_is_at_least_1_41_0("namespaces")

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/namespaces/{name}/resume",
            weaviate_object={},
            error_msg=f"Could not resume namespace '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[202], error="Resume namespace"),
        )

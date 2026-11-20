import uuid
from typing import Generic, Literal, Optional, overload

from httpx import Response

from weaviate.cluster.models import (
    ReplicaAddition,
    ReplicateOperation,
    ReplicateOperations,
    ReplicateOperationWithHistory,
    ReplicateOperationWithoutHistory,
    ReplicationScaleApplyResult,
    ReplicationScalePlan,
    ShardScaleActions,
    _ReplicateOperation,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateUnsupportedFeatureError
from weaviate.types import UUID
from weaviate.util import _capitalize_first_letter

# Check each release branch with _ServerVersion.is_at_least_any so an older
# branch's backport does not incorrectly enable an unpatched newer branch.
_SCALE_PLAN_MIN_VERSIONS = ((1, 31, 20), (1, 32, 17), (1, 33, 5), (1, 34, 1))


class _ReplicateExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def __check_scale_plan_version(self) -> None:
        version = self._connection._weaviate_version
        if not version.is_at_least_any(*_SCALE_PLAN_MIN_VERSIONS):
            minimum_versions = " or ".join(
                ".".join(map(str, minimum)) for minimum in _SCALE_PLAN_MIN_VERSIONS
            )
            raise WeaviateUnsupportedFeatureError(
                "Replication scale plans",
                str(version),
                f"{minimum_versions} on the corresponding release branch",
            )

    def generate_scale_plan(
        self, *, collection: str, replication_factor: int
    ) -> executor.Result[ReplicationScalePlan]:
        """Generate a replication scale plan for a collection.

        Requires replica movement enabled and Weaviate 1.31.20+, 1.32.17+,
        1.33.5+ or 1.34.1+ on the corresponding release branch, or a newer minor release.
        Generating a plan does not change replica placement. Submit the returned plan
        with `apply_scale_plan`, with or without edits.

        Args:
            collection: The name of the collection. Its first letter is capitalized.
            replication_factor: The desired number of replicas per shard. The server rejects
                values below one.

        Returns:
            An editable plan containing per-shard replica additions and removals.

        Raises:
            weaviate.exceptions.WeaviateUnsupportedFeatureError: If the server version
                does not support replication scale plans.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate rejects the request.
        """
        self.__check_scale_plan_version()

        def resp(response: Response) -> ReplicationScalePlan:
            json_response = response.json()
            return ReplicationScalePlan(
                plan_id=uuid.UUID(json_response["planId"]),
                collection=json_response["collection"],
                shard_scale_actions={
                    shard: ShardScaleActions(
                        remove_nodes=actions["removeNodes"],
                        add_nodes=[
                            ReplicaAddition(target_node=target_node, source_node=source_node)
                            for target_node, source_node in actions.get("addNodes", {}).items()
                        ],
                    )
                    for shard, actions in json_response["shardScaleActions"].items()
                },
            )

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/replication/scale",
            params={
                "collection": _capitalize_first_letter(collection),
                "replicationFactor": replication_factor,
            },
            status_codes=_ExpectedStatusCodes(200, "generate replication scale plan"),
            error_msg="Failed to generate replication scale plan",
        )

    def apply_scale_plan(
        self, *, plan: ReplicationScalePlan
    ) -> executor.Result[ReplicationScaleApplyResult]:
        """Apply a replication scale plan.

        Requires replica movement enabled and Weaviate 1.31.20+, 1.32.17+,
        1.33.5+ or 1.34.1+ on the corresponding release branch, or a newer minor release.
        The plan is submitted without modification or regeneration. The server validates
        its actions against the cluster state. This method does not wait for replication
        to complete.

        Args:
            plan: The plan to apply, including any edits. Its collection name is sent as given.

        Returns:
            The accepted plan's ID and collection, and the started replication operation IDs.
            Use `get` to inspect the operations. Removal-only plans may return no operation IDs.

        Raises:
            weaviate.exceptions.WeaviateInvalidInputError: If a shard lists the same target node
                more than once.
            weaviate.exceptions.WeaviateUnsupportedFeatureError: If the server version
                does not support replication scale plans.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate rejects the request.
        """
        self.__check_scale_plan_version()

        shard_scale_actions = {}
        for shard, actions in plan.shard_scale_actions.items():
            add_nodes: dict[str, Optional[str]] = {}
            # Converting duplicate targets to a JSON object would silently drop an addition.
            for addition in actions.add_nodes:
                if addition.target_node in add_nodes:
                    raise WeaviateInvalidInputError(
                        f"Shard {shard!r} contains duplicate target node {addition.target_node!r}"
                    )
                add_nodes[addition.target_node] = addition.source_node
            shard_scale_actions[shard] = {
                "removeNodes": actions.remove_nodes,
                "addNodes": add_nodes,
            }

        def resp(response: Response) -> ReplicationScaleApplyResult:
            json_response = response.json()
            return ReplicationScaleApplyResult(
                plan_id=uuid.UUID(json_response["planId"]),
                collection=json_response["collection"],
                operation_ids=[
                    uuid.UUID(operation_id) for operation_id in json_response["operationIds"] or []
                ],
            )

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path="/replication/scale",
            weaviate_object={
                "planId": str(plan.plan_id),
                "collection": plan.collection,
                "shardScaleActions": shard_scale_actions,
            },
            status_codes=_ExpectedStatusCodes(200, "apply replication scale plan"),
            error_msg="Failed to apply replication scale plan",
        )

    @overload
    def get(
        self, *, uuid: UUID, include_history: Literal[False] = False
    ) -> executor.Result[Optional[ReplicateOperationWithoutHistory]]: ...

    @overload
    def get(
        self, *, uuid: UUID, include_history: Literal[True]
    ) -> executor.Result[Optional[ReplicateOperationWithHistory]]: ...

    def get(
        self, *, uuid: UUID, include_history: bool = False
    ) -> executor.Result[Optional[ReplicateOperation]]:
        """Get the a replicate operation by its UUID.

        Args:
            uuid: The ID of the replicate operation.
            include_history: Whether to include the history of the operation.

        Returns:
            The replicate operation.
        """

        def resp(response: Response):
            if response.status_code == 404:
                return None
            return _ReplicateOperation._from_weaviate(response.json(), include_history)

        params = {}
        if include_history:
            params["includeHistory"] = include_history

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/replication/replicate/{uuid}",
            params=params,
            status_codes=_ExpectedStatusCodes([200, 404], "replicate get"),
            error_msg="Failed to get replicate operation",
        )

    def list_all(self) -> executor.Result[list[ReplicateOperationWithHistory]]:
        """List all replicate operations.

        Returns:
            A list of replicate operations.
        """

        def resp(response: Response) -> list[ReplicateOperationWithHistory]:
            return [_ReplicateOperation._from_weaviate(item, True) for item in response.json()]  # pyright: ignore[reportReturnType]

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/replication/replicate/list",
            params={"includeHistory": True},
            status_codes=_ExpectedStatusCodes(200, "replicate list"),
            error_msg="Failed to list replicate operations",
        )

    @overload
    def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: Literal[True],
    ) -> executor.Result[list[ReplicateOperationWithHistory]]: ...

    @overload
    def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: Literal[False] = False,
    ) -> executor.Result[list[ReplicateOperationWithoutHistory]]: ...

    def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: bool = False,
    ) -> executor.Result[ReplicateOperations]:
        """Query replicate operations by collection, shard, node, or any combination of the three.

        Args:
            collection: The name of the collection of the operation.
            shard: The name of the shard of the operation.
            target_node: The name of the target node of the operation.
            include_history: Whether to include the history of the operation.

        Returns:
            A list of replicate operations specific to the provided parameters.
        """

        def resp(response: Response) -> ReplicateOperations:
            return [
                _ReplicateOperation._from_weaviate(item, include_history)
                for item in response.json()  # pyright: ignore[reportReturnType]
            ]

        params = {}
        if collection:
            params["collection"] = collection
        if shard:
            params["shard"] = shard
        if target_node:
            params["targetNode"] = target_node
        if include_history:
            params["includeHistory"] = include_history

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/replication/replicate/list",
            status_codes=_ExpectedStatusCodes(200, "replicate query"),
            error_msg="Failed to query replicate operations",
            params=params,
        )

    def cancel(
        self,
        *,
        uuid: UUID,
    ) -> executor.Result[None]:
        """Cancel a replicate operation by its UUID.

        Args:
            uuid: The ID of the replicate operation.

        Returns:
            None
        """
        return executor.execute(
            response_callback=lambda _: None,
            method=self._connection.post,
            weaviate_object={},
            path=f"/replication/replicate/{uuid}/cancel",
            status_codes=_ExpectedStatusCodes(204, "replicate cancel"),
            error_msg="Failed to cancel replicate operation",
        )

    def delete(
        self,
        *,
        uuid: UUID,
    ) -> executor.Result[None]:
        """Delete a replicate operation by its UUID.

        Args:
            uuid: The ID of the replicate operation.

        Returns:
            None
        """
        return executor.execute(
            response_callback=lambda _: None,
            method=self._connection.delete,
            path=f"/replication/replicate/{uuid}",
            status_codes=_ExpectedStatusCodes(204, "replicate delete"),
            error_msg="Failed to delete replicate operation",
        )

    def delete_all(self) -> executor.Result[None]:
        """Delete all replicate operations.

        Returns:
            None
        """
        return executor.execute(
            response_callback=lambda _: None,
            method=self._connection.delete,
            path="/replication/replicate",
            status_codes=_ExpectedStatusCodes(204, "replicate delete all"),
            error_msg="Failed to delete all replicate operations",
        )

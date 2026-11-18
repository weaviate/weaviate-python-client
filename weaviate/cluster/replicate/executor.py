from typing import Generic, Literal, Optional, overload

from httpx import Response

from weaviate.cluster.models import (
    ReplicateOperation,
    ReplicateOperations,
    ReplicateOperationWithHistory,
    ReplicateOperationWithoutHistory,
    ReplicationScaleApplyResult,
    ReplicationScalePlan,
    _ReplicateOperation,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.types import UUID

# Check each release branch with _ServerVersion.is_at_least_any so an older
# branch's backport does not incorrectly enable an unpatched newer branch.
_SCALE_PLAN_MIN_VERSIONS = ((1, 31, 20), (1, 32, 17), (1, 33, 5), (1, 34, 1))


class _ReplicateExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def generate_scale_plan(
        self, *, collection: str, replication_factor: int
    ) -> executor.Result[ReplicationScalePlan]:
        """Compute an editable plan for a collection's desired replica count.

        Requires replica movement enabled and Weaviate 1.31.20+, 1.32.17+,
        1.33.5+ or 1.34.1+ on the corresponding release branch. Newer minor
        releases are supported. Generating a plan leaves replica placement
        unchanged; submit it separately with ``apply_scale_plan`` after
        inspection or editing.

        Args:
            collection: Collection name. Its first letter is capitalized.
            replication_factor: Desired replicas per shard. The server rejects
                values below one.

        Returns:
            The server-computed plan with typed per-shard actions and a UUID ID.

        Raises:
            WeaviateUnsupportedFeatureError: The server's release branch does not
                include replication scale plans.
            UnexpectedStatusCodeError: The server rejects the request, including
                an invalid replication factor, a missing collection, or disabled
                replica movement.
        """
        raise NotImplementedError("Replication scale plan generation is not implemented")

    def apply_scale_plan(
        self, *, plan: ReplicationScalePlan
    ) -> executor.Result[ReplicationScaleApplyResult]:
        """Submit a plan's replica changes, including caller edits.

        Requires replica movement enabled and Weaviate 1.31.20+, 1.32.17+,
        1.33.5+ or 1.34.1+ on the corresponding release branch. Newer minor
        releases are supported. The supplied plan is submitted without mutation
        or regeneration. The server validates its actions against the cluster
        state.

        Args:
            plan: The plan to apply, including its ID, collection and shard actions.
                ``plan.collection`` is sent as given, without capitalization;
                plans from ``generate_scale_plan`` already carry the server's name.

        Returns:
            The accepted plan's identity and initiated shard-copy operation IDs.
            This call does not wait for replication to complete. Inspect the IDs
            with ``get``. A removal-only plan may return no operation IDs.

        Raises:
            WeaviateInvalidInputError: A shard lists the same target node in more
                than one ``ReplicaAddition``.
            WeaviateUnsupportedFeatureError: The server's release branch does not
                include replication scale plans.
            UnexpectedStatusCodeError: The server rejects the request, including
                an invalid plan or disabled replica movement.
        """
        raise NotImplementedError("Replication scale plan application is not implemented")

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

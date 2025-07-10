from typing import Generic, Literal, Optional, overload

from httpx import Response

from weaviate.cluster.models import (
    ReplicateOperation,
    ReplicateOperations,
    ReplicateOperationWithHistory,
    ReplicateOperationWithoutHistory,
    _ReplicateOperation,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.types import UUID


class _ReplicateExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

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

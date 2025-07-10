import uuid
from typing import Generic, List, Optional, Union

from httpx import Response

from weaviate.cluster.models import (
    ReplicationType,
    ShardingState,
)
from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import NodeMinimal, NodeVerbose, _ConvertFromREST
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.exceptions import EmptyResponseError
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict


class _ClusterExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def replicate(
        self,
        *,
        collection: str,
        shard: str,
        source_node: str,
        target_node: str,
        replication_type: ReplicationType = ReplicationType.COPY,
    ) -> executor.Result[uuid.UUID]:
        """Replicate a shard from one node to another.

        Args:
            collection: The name of the collection.
            shard: The name of the shard.
            source_node: The source node.
            target_node: The target node.
            replication_type: The type of replication (COPY or MOVE).

        Returns:
            A UUID representing the replicate task.
        """

        def resp(response: Response):
            return uuid.UUID(response.json()["id"])

        body = {
            "collection": collection,
            "shard": shard,
            "sourceNode": source_node,
            "targetNode": target_node,
            "type": replication_type.value,
        }
        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path="/replication/replicate",
            weaviate_object=body,
            status_codes=_ExpectedStatusCodes(200, "replicate replicate"),
            error_msg="Failed to replicate shard",
        )

    def query_sharding_state(
        self,
        *,
        collection: str,
        shard: Optional[str] = None,
    ) -> executor.Result[Optional[ShardingState]]:
        """Query the sharding state of a collection or shard.

        If shard is None, the state of all shards in the collection will be returned.

        Args:
            collection: The name of the collection.
            shard: The name of the shard.

        Returns:
            The sharding state or None if the collection or shard does not exist.
        """

        def resp(response: Response):
            if response.status_code == 404:
                return None
            return ShardingState._from_weaviate(response.json())

        params = {"collection": collection}
        if shard is not None:
            params["shard"] = shard

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/replication/sharding-state",
            params=params,
            status_codes=_ExpectedStatusCodes([200, 404], "replicate sharding state"),
            error_msg="Failed to get sharding state",
        )

    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Optional[Verbosity] = None,
    ) -> executor.Result[Union[List[NodeMinimal], List[NodeVerbose]]]:
        """Get the status of all nodes in the cluster.

        Args:
            collection: Get the status for the given collection. If not given all collections will be included.
            shard: Get the status for the given shard. If not given all shards will be included.
            output: Set the desired output verbosity level. Can be [`minimal` | `verbose`], defaults to `None`, which is server-side default of `minimal`.

        Returns:
            List of nodes and their respective status.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
            weaviate.EmptyResponseError: If the response is empty.
        """
        path = "/nodes"
        params = {}
        if collection is not None:
            path += "/" + _capitalize_first_letter(collection)
        if shard is not None:
            params["shardName"] = shard
        if output is not None:
            params["output"] = output

        def resp(
            res: Response,
        ) -> Union[List[NodeMinimal], List[NodeVerbose]]:
            response_typed = _decode_json_response_dict(res, "Nodes status")
            assert response_typed is not None

            nodes = response_typed.get("nodes")
            if nodes is None or nodes == []:
                raise EmptyResponseError("Nodes status response returned empty")

            if output == "verbose":
                return _ConvertFromREST.nodes_verbose(nodes)
            else:
                return _ConvertFromREST.nodes_minimal(nodes)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params=params,
            error_msg="Get nodes status failed",
        )

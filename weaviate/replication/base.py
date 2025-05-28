import uuid
from typing import Generic, Optional

from httpx import Response

from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.replication.models import (
    ShardingState,
    TransferType,
)


class _ReplicationExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def replicate(
        self,
        *,
        collection: str,
        shard: str,
        source_node: str,
        target_node: str,
        transfer_type: TransferType,
    ) -> executor.Result[uuid.UUID]:
        def resp(response: Response):
            return uuid.UUID(response.json()["id"])

        body = {
            "collectionId": collection,
            "shardId": shard,
            "sourceNodeName": source_node,
            "destinationNodeName": target_node,
            "transferType": transfer_type.value,
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
        shard: Optional[str],
    ) -> executor.Result[Optional[ShardingState]]:
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

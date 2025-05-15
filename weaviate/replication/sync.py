import uuid
from typing import Optional

from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.replication.base import _ReplicationExecutor
from weaviate.replication.models import ShardingState, TransferType
from weaviate.replication.operations.sync import _Operations


class _Replication:
    def __init__(self, connection: ConnectionSync) -> None:
        self.operations = _Operations(connection)
        self.__executor = _ReplicationExecutor(connection)

    def replicate(
        self,
        *,
        collection: str,
        shard: str,
        source_node: str,
        target_node: str,
        transfer_type: TransferType = TransferType.COPY,
    ) -> uuid.UUID:
        """Replicate a shard from one node to another.

        Args:
            collection: The name of the collection.
            shard: The name of the shard.
            source_node: The source node.
            target_node: The target node.
            transfer_type: The type of transfer (COPY or MOVE).

        Returns:
            A UUID representing the replicate task.
        """
        return executor.result(
            self.__executor.replicate(
                collection=collection,
                shard=shard,
                source_node=source_node,
                target_node=target_node,
                transfer_type=transfer_type,
            )
        )

    def query_sharding_state(
        self,
        *,
        collection: str,
        shard: Optional[str] = None,
    ) -> ShardingState:
        """Query the sharding state of a collection or shard.

        If shard is None, the state of all shards in the collection will be returned.

        Args:
            collection: The name of the collection.
            shard: The name of the shard.

        Returns:
            The sharding state.
        """
        return executor.result(
            self.__executor.query_sharding_state(
                collection=collection,
                shard=shard,
            )
        )

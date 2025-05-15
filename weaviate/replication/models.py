import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Generic, List, Literal, Optional, TypedDict, TypeVar


class TransferType(str, Enum):
    """Enum for transfer types."""

    COPY = "COPY"
    MOVE = "MOVE"


class ReplicateOperationState(str, Enum):
    """Enum for replication operation states."""

    REGISTERED = "REGISTERED"
    HYDRATING = "HYDRATING"
    FINALIZING = "FINALIZING"
    DEHYDRATING = "DEHYDRATING"
    READY = "READY"
    CANCELLED = "CANCELLED"


class _ReplicationReplicateDetailsReplicaStatus(TypedDict):
    state: Literal["REGISTERED", "HYDRATING", "FINALIZING", "DEHYDRATING", "READY", "CANCELLED"]
    errors: List[str]


class _ReplicationReplicateDetailsReplicaResponse(TypedDict):
    collectionId: str
    shardId: str
    sourceNodeName: str
    destinationNodeName: str
    status: _ReplicationReplicateDetailsReplicaStatus
    statusHistory: Optional[List[_ReplicationReplicateDetailsReplicaStatus]]
    transferType: Literal["COPY", "MOVE"]
    id: str  # noqa: A003


@dataclass
class ReplicateOperationStatus:
    """Class representing the status of a replication operation."""

    state: ReplicateOperationState
    errors: List[str]

    @classmethod
    def _from_weaviate(
        cls, data: _ReplicationReplicateDetailsReplicaStatus
    ) -> "ReplicateOperationStatus":
        return cls(
            state=ReplicateOperationState(data["state"]),
            errors=data["errors"],
        )


H = TypeVar("H", None, List[ReplicateOperationStatus])


@dataclass
class ReplicateOperation(Generic[H]):
    """Class representing a replication operation."""

    collection: str
    shard: str
    source_node: str
    status: ReplicateOperationStatus
    status_history: H
    target_node: str
    transfer_type: TransferType
    uuid: uuid.UUID

    @staticmethod
    def _from_weaviate(
        data: _ReplicationReplicateDetailsReplicaResponse,
        include_history: bool = True,
    ):
        common = {
            "collection": data["collection"],
            "shard": data["shardId"],
            "source_node": data["sourceNodeId"],
            "status": ReplicateOperationStatus._from_weaviate(data["status"]),
            "target_node": data["targetNodeId"],
            "transfer_type": TransferType(data["transferType"]),
            "uuid": uuid.UUID(data["id"]),
        }
        if include_history and data["statusHistory"] is not None:
            return ReplicateOperation(
                **common,
                status_history=[
                    ReplicateOperationStatus._from_weaviate(status)
                    for status in data["statusHistory"]
                ],
            )
        return ReplicateOperation(
            **common,
            status_history=None,
        )


class _ReplicationShardReplicas(TypedDict):
    shard: str
    replicas: List[str]


class _ReplicationShardingState(TypedDict):
    collection: str
    shards: List[_ReplicationShardReplicas]


class _ReplicationShardingStateResponse(TypedDict):
    shardingState: _ReplicationShardingState


@dataclass
class ShardReplicas:
    """Class representing a shard replica."""

    name: str
    replicas: List[str]

    @staticmethod
    def _from_weaviate(data: _ReplicationShardReplicas):
        return ShardReplicas(
            name=data["shard"],
            replicas=data["replicas"],
        )


@dataclass
class ShardingState:
    """Class representing the sharding state of a collection."""

    collection: str
    shards: List[ShardReplicas]

    @staticmethod
    def _from_weaviate(data: _ReplicationShardingStateResponse):
        ss = data["shardingState"]
        return ShardingState(
            collection=ss["collection"],
            shards=[ShardReplicas._from_weaviate(shard) for shard in ss["shards"]],
        )

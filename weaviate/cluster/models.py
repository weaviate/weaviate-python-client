import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Generic, List, TypedDict, TypeVar, Union


class ReplicationType(str, Enum):
    """Enum for replication types."""

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


@dataclass
class ReplicateOperationStatus:
    """Class representing the status of a replication operation."""

    state: ReplicateOperationState
    errors: List[str]

    @classmethod
    def _from_weaviate(cls, data: dict) -> "ReplicateOperationStatus":
        return cls(
            state=ReplicateOperationState(data["state"]),
            errors=data["errors"] or [],
        )


H = TypeVar("H", None, List[ReplicateOperationStatus])


@dataclass
class _ReplicateOperation(Generic[H]):
    """Class representing a replication operation."""

    collection: str
    shard: str
    source_node: str
    status: ReplicateOperationStatus
    status_history: H
    target_node: str
    transfer_type: ReplicationType
    uuid: uuid.UUID

    @staticmethod
    def _from_weaviate(
        data: dict,
        include_history: bool,
    ):
        common = {
            "collection": data["collection"],
            "shard": data["shard"],
            "source_node": data["sourceNode"],
            "status": ReplicateOperationStatus._from_weaviate(data["status"]),
            "target_node": data["targetNode"],
            "transfer_type": ReplicationType(data["type"]),
            "uuid": uuid.UUID(data["id"]),
        }
        if include_history and data["statusHistory"] is not None:
            return _ReplicateOperation(
                **common,
                status_history=[
                    ReplicateOperationStatus._from_weaviate(status)
                    for status in data["statusHistory"]
                ],
            )
        return _ReplicateOperation(
            **common,
            status_history=None,
        )


ReplicateOperationWithoutHistory = _ReplicateOperation[None]
ReplicateOperationWithHistory = _ReplicateOperation[List[ReplicateOperationStatus]]

ReplicateOperation = Union[ReplicateOperationWithoutHistory, ReplicateOperationWithHistory]
ReplicateOperations = Union[
    List[ReplicateOperationWithoutHistory], List[ReplicateOperationWithHistory]
]


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

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Generic, List, TypedDict, TypeVar, Union


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


# --- RAFT cluster statistics ---


@dataclass
class RaftConfigurationMember:
    """A member in the RAFT cluster's latest configuration."""

    address: str
    node_id: str
    suffrage: int

    @staticmethod
    def _from_weaviate(data: dict) -> "RaftConfigurationMember":
        return RaftConfigurationMember(
            address=data["address"],
            node_id=data["id"],
            suffrage=data["suffrage"],
        )


@dataclass
class RaftStats:
    """RAFT consensus statistics for a node."""

    applied_index: str
    commit_index: str
    fsm_pending: str
    last_contact: str
    last_log_index: str
    last_log_term: str
    last_snapshot_index: str
    last_snapshot_term: str
    latest_configuration: List[RaftConfigurationMember]
    latest_configuration_index: str
    num_peers: str
    protocol_version: str
    protocol_version_max: str
    protocol_version_min: str
    snapshot_version_max: str
    snapshot_version_min: str
    state: str
    term: str

    @staticmethod
    def _from_weaviate(data: dict) -> "RaftStats":
        return RaftStats(
            applied_index=data.get("appliedIndex", ""),
            commit_index=data.get("commitIndex", ""),
            fsm_pending=data.get("fsmPending", ""),
            last_contact=data.get("lastContact", ""),
            last_log_index=data.get("lastLogIndex", ""),
            last_log_term=data.get("lastLogTerm", ""),
            last_snapshot_index=data.get("lastSnapshotIndex", ""),
            last_snapshot_term=data.get("lastSnapshotTerm", ""),
            latest_configuration=[
                RaftConfigurationMember._from_weaviate(m)
                for m in data.get("latestConfiguration", [])
            ],
            latest_configuration_index=data.get("latestConfigurationIndex", ""),
            num_peers=data.get("numPeers", ""),
            protocol_version=data.get("protocolVersion", ""),
            protocol_version_max=data.get("protocolVersionMax", ""),
            protocol_version_min=data.get("protocolVersionMin", ""),
            snapshot_version_max=data.get("snapshotVersionMax", ""),
            snapshot_version_min=data.get("snapshotVersionMin", ""),
            state=data.get("state", ""),
            term=data.get("term", ""),
        )


@dataclass
class NodeStatistics:
    """RAFT cluster statistics for a single node."""

    candidates: Dict[str, Any]
    db_loaded: bool
    initial_last_applied_index: int
    is_voter: bool
    leader_address: str
    leader_id: str
    name: str
    is_open: bool
    raft: RaftStats
    ready: bool
    status: str

    @staticmethod
    def _from_weaviate(data: dict) -> "NodeStatistics":
        return NodeStatistics(
            candidates=data.get("candidates", {}),
            db_loaded=data.get("dbLoaded", False),
            initial_last_applied_index=data.get("initialLastAppliedIndex", 0),
            is_voter=data.get("isVoter", False),
            leader_address=data.get("leaderAddress", ""),
            leader_id=data.get("leaderId", ""),
            name=data.get("name", ""),
            is_open=data.get("open", False),
            raft=RaftStats._from_weaviate(data.get("raft", {})),
            ready=data.get("ready", False),
            status=data.get("status", ""),
        )


@dataclass
class ClusterStatistics:
    """Response from GET /v1/cluster/statistics (RAFT cluster statistics)."""

    statistics: List[NodeStatistics]
    synchronized: bool

    @staticmethod
    def _from_weaviate(data: dict) -> "ClusterStatistics":
        return ClusterStatistics(
            statistics=[NodeStatistics._from_weaviate(s) for s in data.get("statistics", [])],
            synchronized=data.get("synchronized", False),
        )

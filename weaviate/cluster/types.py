from typing import List, Literal, Optional, TypedDict, Dict


class BatchStats(TypedDict):
    queueLength: int
    ratePerSecond: int


# must use functional syntax because class is a keyword
Shard = TypedDict(
    "Shard",
    {
        "name": str,
        "class": str,
        "objectCount": int,
        "vectorIndexingStatus": Literal["READONLY", "INDEXING", "READY"],
        "vectorQueueLength": int,
        "compressed": bool,
        "loaded": Optional[bool],
    },
)


class Stats(TypedDict):
    objectCount: int
    shardCount: int


class Node(TypedDict):
    batchStats: BatchStats
    gitHash: str
    name: str
    shards: Optional[List[Shard]]
    stats: Stats
    status: str
    version: str


class RaftPeer(TypedDict):
    address: str
    id_: str
    suffrage: int


class RaftStats(TypedDict):
    appliedIndex: str
    commitIndex: str
    fsmPending: str
    lastContact: str
    lastLogIndex: str
    lastLogTerm: str
    lastSnapshotIndex: str
    lastSnapshotTerm: str
    latestConfiguration: List[RaftPeer]
    latestConfigurationIndex: str
    numPeers: str
    protocolVersion: str
    protocolVersionMax: str
    protocolVersionMin: str
    snapshotVersionMax: str
    snapshotVersionMin: str
    state: str
    term: str


# total=False is used to make handle some of the optional fields
class ClusterNodeStats(TypedDict, total=False):
    bootstrapped: bool
    candidates: Dict[str, str]
    dbLoaded: bool
    isVoter: bool
    leaderAddress: str
    leaderId: str
    name: str
    open_: bool
    raft: RaftStats
    ready: bool
    status: str


class ClusterStats(TypedDict):
    statistics: List[ClusterNodeStats]
    synchronized: bool

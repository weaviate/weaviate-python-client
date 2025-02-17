from typing import List, Literal, Optional, TypedDict


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


Verbosity = Literal["minimal", "verbose"]

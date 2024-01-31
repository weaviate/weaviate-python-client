from typing import List, Optional, TypedDict


class BatchStats(TypedDict):
    queueLength: int
    ratePerSecond: int


# must use functional syntax because class is a keyword
Shard = TypedDict("Shard", {"class": str, "name": str, "objectCount": int})


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

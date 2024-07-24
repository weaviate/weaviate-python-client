from dataclasses import dataclass
from typing import Generic, List, Literal, Optional, TypeVar, cast

from weaviate.cluster.types import Node as NodeREST, Shard as ShardREST


@dataclass
class Shard:
    """The properties of a single shard of a collection."""

    collection: str
    name: str
    node: str
    object_count: int
    vector_indexing_status: Literal["READONLY", "INDEXING", "READY"]
    vector_queue_length: int
    compressed: bool
    loaded: Optional[bool]  # not present in <1.24.x


@dataclass
class Stats:
    """The statistics of a collection."""

    object_count: int
    shard_count: int


Shards = List[Shard]
Sh = TypeVar("Sh")
St = TypeVar("St")


@dataclass
class Node(Generic[Sh, St]):
    """The properties of a single node in the cluster."""

    git_hash: str
    name: str
    shards: Sh
    stats: St
    status: str
    version: str


class _ConvertFromREST:
    @staticmethod
    def nodes_verbose(nodes: List[NodeREST]) -> List[Node[Shards, Stats]]:
        return [
            Node(
                git_hash=node.get("gitHash", "None"),
                name=node["name"],
                shards=(
                    [
                        Shard(
                            collection=shard["class"],
                            name=shard["name"],
                            node=node["name"],
                            object_count=shard["objectCount"],
                            vector_indexing_status=shard["vectorIndexingStatus"],
                            vector_queue_length=shard["vectorQueueLength"],
                            compressed=shard["compressed"],
                            loaded=shard.get("loaded"),
                        )
                        for shard in cast(List[ShardREST], node["shards"])
                    ]
                    if "shards" in node and node["shards"] is not None
                    else []
                ),
                stats=(
                    Stats(
                        object_count=node["stats"]["objectCount"],
                        shard_count=node["stats"]["shardCount"],
                    )
                    if "stats" in node
                    else Stats(
                        object_count=0,
                        shard_count=0,
                    )
                ),
                status=node["status"],
                version=node.get("version", ""),
            )
            for node in nodes
        ]

    @staticmethod
    def nodes_minimal(nodes: List[NodeREST]) -> List[Node[None, None]]:
        return [
            Node(
                git_hash=node.get("gitHash", "None"),
                name=node["name"],
                shards=None,
                stats=None,
                status=node["status"],
                version=node.get("version", ""),
            )
            for node in nodes
        ]

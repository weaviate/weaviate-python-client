from dataclasses import dataclass
from typing import Generic, List, TypeVar, cast

from weaviate.cluster.types import Node as NodeREST, Shard as ShardREST


@dataclass
class Shard:
    """The properties of a single shard of a collection."""

    collection: str
    name: str
    node: str
    object_count: int


@dataclass
class Stats:
    """The statistics of a collection."""

    object_count: int
    shard_count: int


Shards = List[Shard]
S = TypeVar("S")


@dataclass
class Node(Generic[S]):
    """The properties of a single node in the cluster."""

    git_hash: str
    name: str
    shards: S
    stats: Stats
    status: str
    version: str


class _ConvertFromREST:
    @staticmethod
    def nodes_verbose(nodes: List[NodeREST]) -> List[Node[Shards]]:
        return [
            Node(
                git_hash=node["gitHash"],
                name=node["name"],
                shards=[
                    Shard(
                        collection=shard["class"],
                        name=shard["name"],
                        node=node["name"],
                        object_count=shard["objectCount"],
                    )
                    for shard in cast(List[ShardREST], node["shards"])
                ],
                stats=Stats(
                    object_count=node["stats"]["objectCount"],
                    shard_count=node["stats"]["shardCount"],
                ),
                status=node["status"],
                version=node["version"],
            )
            for node in nodes
        ]

    @staticmethod
    def nodes_minimal(nodes: List[NodeREST]) -> List[Node[None]]:
        return [
            Node(
                git_hash=node["gitHash"],
                name=node["name"],
                shards=None,
                stats=Stats(
                    object_count=node["stats"]["objectCount"],
                    shard_count=node["stats"]["shardCount"],
                ),
                status=node["status"],
                version=node["version"],
            )
            for node in nodes
        ]

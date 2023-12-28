from dataclasses import dataclass
from typing import List


@dataclass
class Shard:
    """The properties of a single shard of a collection.

    If multi-tenancy is enabled, this corresponds to a single tenant. Otherwise, this corresponds to the collection.
    """

    collection: str
    name: str
    object_count: int


class _ConvertFromREST:
    @staticmethod
    def convert_nodes_to_shards(nodes: List[dict]) -> List[Shard]:
        shards: List[Shard] = []
        for node in nodes:
            if (node_shards := node.get("shards")) is not None:
                shards.extend(
                    [
                        Shard(
                            collection=shard.get("class"),
                            name=shard.get("name"),
                            object_count=shard.get("objectCount"),
                        )
                        for shard in node_shards
                    ]
                )
        return shards

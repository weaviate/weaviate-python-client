from typing import List, Literal, Optional, Union, overload

from weaviate.collections.classes.cluster import Node, Shards, Stats
from weaviate.collections.cluster.asy import _ClusterAsync
from weaviate.event_loop import _EventLoop


class _Cluster:
    def __init__(self, event_loop: _EventLoop, cluster: _ClusterAsync):
        self.__event_loop = event_loop
        self.__cluster = cluster

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[Node[None, None]]:
        ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[Node[None, None]]:
        ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[Node[Shards, Stats]]:
        ...

    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Optional[Literal["minimal", "verbose"]] = None,
    ) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]:
        """
        Get the status of all nodes in the cluster.

        Arguments:
            `collection`
                Get the status for the given collection. If not given all collections will be included.
            `output`
                Set the desired output verbosity level. Can be [`minimal` | `verbose`], defaults to `None`, which is server-side default of `minimal`.

        Returns:
            List of nodes and their respective status.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If weaviate reports a none OK status.
            `weaviate.EmptyResponseError`
                If the response is empty.
        """
        return self.__event_loop.run_until_complete(self.__cluster.nodes, collection, output=output)

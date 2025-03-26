from abc import abstractmethod
from typing import Generic, List, Optional, Union

from weaviate.collections.cluster.executor import _ClusterExecutor
from weaviate.collections.classes.cluster import Node, Shards, Stats
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.cluster.types import Verbosity


class _ClusterBase(Generic[ConnectionType]):
    _executor = _ClusterExecutor()

    def __init__(self, connection: ConnectionType):
        self._connection: ConnectionType = connection

    @abstractmethod
    def nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Verbosity] = None,
    ) -> ExecutorResult[Union[List[Node[None, None]], List[Node[Shards, Stats]]]]:
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
        raise NotImplementedError()

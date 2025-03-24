from weaviate.connect.v4 import ConnectionAsync, ConnectionType

from typing import Generic, List, Literal, Optional, Union, overload

from weaviate.collections.cluster.executor import _ClusterExecutor
from weaviate.collections.classes.cluster import Node, Shards, Stats
from weaviate.cluster.types import Verbosity
from weaviate.connect.executor import aresult


class _ClusterBase(Generic[ConnectionType]):
    _executor = _ClusterExecutor()

    def __init__(self, connection: ConnectionType):
        self._connection: ConnectionType = connection


class _ClusterAsync(_ClusterBase[ConnectionAsync]):
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[Node[None, None]]: ...

    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[Node[None, None]]: ...

    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[Node[Shards, Stats]]: ...

    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Verbosity] = None,
    ) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]: ...

    async def nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Verbosity] = None,
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
        return await aresult(
            self._executor.nodes(collection, connection=self._connection, output=output)
        )

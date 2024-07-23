from weaviate.connect import ConnectionV4


from typing import List, Literal, Optional, Union, overload

from weaviate.collections.classes.cluster import Node, Shards, _ConvertFromREST, Stats
from weaviate.exceptions import (
    EmptyResponseError,
)

from weaviate.util import _capitalize_first_letter, _decode_json_response_dict


class _ClusterBase:
    def __init__(self, connection: ConnectionV4):
        self._connection = connection


class _ClusterAsync(_ClusterBase):
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[Node[None, None]]:
        ...

    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[Node[None, None]]:
        ...

    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[Node[Shards, Stats]]:
        ...

    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Literal["minimal", "verbose"]] = None,
    ) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]:
        ...

    async def nodes(
        self,
        collection: Optional[str] = None,
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
        path = "/nodes"
        if collection is not None:
            path += "/" + _capitalize_first_letter(collection)
        if output is not None:
            path += f"?output={output}"

        response = await self._connection.get(path=path, error_msg="Get nodes status failed")
        response_typed = _decode_json_response_dict(response, "Nodes status")
        assert response_typed is not None

        nodes = response_typed.get("nodes")
        if nodes is None or nodes == []:
            raise EmptyResponseError("Nodes status response returned empty")

        if output == "verbose":
            return _ConvertFromREST.nodes_verbose(nodes)
        else:
            return _ConvertFromREST.nodes_minimal(nodes)

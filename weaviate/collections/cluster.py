from typing import List, Literal, Optional, Union, overload

from httpx import ConnectError

from weaviate.collections.classes.cluster import Node, Shards, _ConvertFromREST
from weaviate.connect import ConnectionV4
from weaviate.exceptions import (
    EmptyResponseError,
)
from ..util import _capitalize_first_letter, _decode_json_response_dict


class _Cluster:
    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[Node[None]]:
        ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[Node[None]]:
        ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[Node[Shards]]:
        ...

    def nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Literal["minimal", "verbose"]] = None,
    ) -> Union[List[Node[None]], List[Node[Shards]]]:
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
            `requests.ConnectionError`
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

        try:
            response = self._connection.get(path=path)
        except ConnectError as conn_err:
            raise ConnectError("Get nodes status failed due to connection error") from conn_err

        response_typed = _decode_json_response_dict(response, "Nodes status")
        assert response_typed is not None

        nodes = response_typed.get("nodes")
        if nodes is None or nodes == []:
            raise EmptyResponseError("Nodes status response returned empty")

        return (
            _ConvertFromREST.nodes_verbose(nodes)
            if output == "verbose"
            else _ConvertFromREST.nodes_minimal(nodes)
        )

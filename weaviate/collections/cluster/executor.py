from typing import Generic, List, Literal, Optional, Union, overload

from httpx import Response
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType

from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import Node, Shards, _ConvertFromREST, Stats
from weaviate.exceptions import (
    EmptyResponseError,
)

from weaviate.util import _capitalize_first_letter, _decode_json_response_dict


class _ClusterExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> executor.Result[List[Node[None, None]]]: ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> executor.Result[List[Node[None, None]]]: ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> executor.Result[List[Node[Shards, Stats]]]: ...

    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Optional[Verbosity] = None,
    ) -> executor.Result[Union[List[Node[None, None]], List[Node[Shards, Stats]]]]: ...

    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Optional[Verbosity] = None,
    ) -> executor.Result[Union[List[Node[None, None]], List[Node[Shards, Stats]]]]:
        """Get the status of all nodes in the cluster.

        Args:
            collection: Get the status for the given collection. If not given all collections will be included.
            output: Set the desired output verbosity level. Can be [`minimal` | `verbose`], defaults to `None`, which is server-side default of `minimal`.

        Returns:
            List of nodes and their respective status.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
            weaviate.EmptyResponseError: If the response is empty.
        """
        path = "/nodes"
        params = None
        if collection is not None:
            path += "/" + _capitalize_first_letter(collection)
        if output is not None:
            params = {"output": output}

        def resp(res: Response) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]:
            response_typed = _decode_json_response_dict(res, "Nodes status")
            assert response_typed is not None

            nodes = response_typed.get("nodes")
            if nodes is None or nodes == []:
                raise EmptyResponseError("Nodes status response returned empty")

            if output == "verbose":
                return _ConvertFromREST.nodes_verbose(nodes)
            else:
                return _ConvertFromREST.nodes_minimal(nodes)

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params=params,
            error_msg="Get nodes status failed",
        )

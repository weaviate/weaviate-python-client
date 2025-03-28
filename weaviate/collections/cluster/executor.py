from httpx import Response
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.connect.v4 import Connection


from typing import List, Optional, Union

from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import Node, Shards, _ConvertFromREST, Stats
from weaviate.exceptions import (
    EmptyResponseError,
)

from weaviate.util import _capitalize_first_letter, _decode_json_response_dict


class _ClusterExecutor:
    def __init__(self, connection: Connection):
        self._connection = connection

    def nodes(
        self,
        collection: Optional[str],
        *,
        output: Optional[Verbosity],
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

        return execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params=params,
            error_msg="Get nodes status failed",
        )

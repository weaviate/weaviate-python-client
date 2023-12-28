from typing import List

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collections.classes.meta import Shard, _ConvertFromREST
from weaviate.connect import Connection
from weaviate.exceptions import (
    EmptyResponseException,
)
from ..util import _capitalize_first_letter, _decode_json_response_dict


class _Meta:
    def __init__(self, connection: Connection, name: str):
        self._connection = connection
        self.__name: str = name

    def get_shards(
        self,
    ) -> List[Shard]:
        """
        Get the statuses of all the shards of this collection.

        If the collection is multi-tenancy, each shard is one of the tenants. If the collection is single-tenancy, there is only one shard.

        Arguments:
            `output`
                Set the desired output verbosity level. Can be `[minimal | verbose]`, defaults to server-side default of `minimal`.

        Returns:
            The list of shards belonging to this collection.

        Raises
            `requests.ConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If weaviate reports a none OK status.
            `weaviate.EmptyResponseException`
                If the response is empty.
        """
        path = f"/nodes/{_capitalize_first_letter(self.__name)}?output=verbose"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Get nodes status failed due to connection error"
            ) from conn_err

        response_typed = _decode_json_response_dict(response, "Nodes status")
        assert response_typed is not None

        nodes = response_typed.get("nodes")
        if nodes is None or nodes == []:
            raise EmptyResponseException("Nodes status response returned empty")

        return _ConvertFromREST.convert_nodes_to_shards(nodes)

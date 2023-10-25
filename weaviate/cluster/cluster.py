"""
Cluster class definition.
"""
from typing import List, Literal, Optional, cast

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import (
    EmptyResponseException,
)
from ..util import _capitalize_first_letter, _decode_json_response_dict


class Cluster:
    """
    Cluster class used for cluster information
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Cluster class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection

    def get_nodes_status(self, class_name: Optional[str] = None) -> list:
        """
        Get the nodes status.

        Parameters
        ----------
        class_name : Optional[str]
            Get the status for the given class. If not given all classes will be included.

        Returns
        -------
        list
            List of nodes and their respective status.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        weaviate.EmptyResponseException
            If the response is empty.
        """
        path = "/nodes"
        if class_name is not None:
            path += "/" + _capitalize_first_letter(class_name)

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
        return cast(list, nodes)

    def get_shard_indexing_status(
        self, class_name: str
    ) -> Literal["READY", "INDEXING", "READ-ONLY"]:
        nodes = self.get_nodes_status(class_name)
        for node in nodes:
            shards: List[dict] = node.get("shards", [])
            for shard in shards:
                if shard["class"] == class_name:
                    return shard.get("vectorIndexingStatus", "READY")
        raise EmptyResponseException("Shard indexing status response returned empty")

    def get_global_indexing_status(self) -> Literal["READY", "INDEXING", "READ-ONLY"]:
        nodes = self.get_nodes_status()
        statuses: List[Literal["READY", "INDEXING", "READ-ONLY"]] = []

        for node in nodes:
            shards: List[dict] = node.get("shards", [])
            statuses.extend([shard.get("vectorIndexingStatus", "READY") for shard in shards])

        if len(statuses) == 0:
            return "READY"
        if "INDEXING" in statuses:
            return "INDEXING"
        if "READ-ONLY" in statuses:
            return "READ-ONLY"
        return "READY"

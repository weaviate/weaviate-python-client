"""
Cluster class definition.
"""
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    EmptyResponseException,
)


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

    def get_nodes_status(self) -> list:
        """
        Get the nodes status.

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

        try:
            response = self._connection.get(
                path="/nodes",
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Get nodes status failed due to connection error"
            ) from conn_err

        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Nodes status", response)
        nodes = response.json().get("nodes")
        if nodes is None or nodes == []:
            raise EmptyResponseException("Nodes status response returned empty")
        return nodes

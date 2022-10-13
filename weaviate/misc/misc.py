from weaviate.connect import Connection
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    RequestsConnectionError,
    EmptyResponseException
)

class Misc:
    """
    Misc class used for system information
    """
    
    def __init__(self, connection: Connection):
        """
        Initialize a Misc class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection

    def get_nodes_status(self) -> list:
        try:
            resp = self._connection.get(path="/nodes")
            if resp.status_code != 200:
                raise UnexpectedStatusCodeException("Nodes status", resp) 
            nodes: list = resp.json().get('nodes')
            if nodes == None or nodes == []:
                raise EmptyResponseException("Nodes status response returned empty")
            return nodes
        except RequestsConnectionError as e:
            raise RequestsConnectionError(
                "Get nodes status failed due to connection error"
            ) from e

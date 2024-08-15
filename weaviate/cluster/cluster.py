"""
Cluster class definition.
"""

from typing import List, Literal, Optional, cast

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.cluster.types import Node
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

    def get_nodes_status(
        self,
        class_name: Optional[str] = None,
        output: Optional[Literal["minimal", "verbose"]] = None,
    ) -> List[Node]:
        """
        Get the nodes status.

        Parameters
        ----------
        class_name : Optional[str]
            Get the status for the given class. If not given all classes will be included.
        output : Optional[str]
            Set the desired output verbosity level. Can be [minimal | verbose], defaults to minimal.

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
        if output is not None:
            path += f"?output={output}"

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
        return cast(List[Node], nodes)

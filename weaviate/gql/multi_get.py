"""
GraphQL `Get` command.
"""

from typing import List, Optional
from weaviate.gql.filter import (
    GraphQL,
)
from weaviate.connect import Connection


class MultiGetBuilder(GraphQL):
    """
    GetBuilder class used to create GraphQL queries.
    """

    def __init__(self, get: Optional[List], connection: Connection):
        """
        Initialize a GetBuilder class instance.

        Parameters
        ----------
        class_name : str
            Class name of the objects to interact with.
        properties : str or list of str
            Properties of the objects to interact with.
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.

        Raises
        ------
        TypeError
            If argument/s is/are of wrong type.
        """

        super().__init__(connection)
        self.get: List[str] = get

    def build(self) -> str:
        """
        Build query filter as a string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """
        query = "{Get{"

        for get in self.get:
            if get._alias is not None:
                query += get._alias + ": "
            query += get._class_name
            if get._contains_filter:
                query += "("
                if get._where is not None:
                    query += str(get._where)
                if get._limit is not None:
                    query += get._limit
                if get._offset is not None:
                    query += get._offset
                if get._near_ask is not None:
                    query += str(get._near_ask)
                if get._sort is not None:
                    query += str(get._sort)
                if get._bm25 is not None:
                    query += str(get._bm25)
                if get._hybrid is not None:
                    query += str(get._hybrid)
                query += ")"

            additional_props = get._additional_to_str()

            if not (additional_props or get._properties):
                raise AttributeError(
                    "No 'properties' or 'additional properties' specified to be returned. "
                    "At least one should be included."
                )

            properties = " ".join(get._properties) + get._additional_to_str()
            query += "{" + properties + "}"
        return query + "}}"

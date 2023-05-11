"""
GraphQL query module.
"""
from typing import List, Union

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.schema.crud_schema import Schema
from .aggregate import AggregateBuilder
from .get import GetBuilder
from .multi_get import MultiGetBuilder


class Query:
    """
    Query class used to make `get` and/or `aggregate` GraphQL queries.
    """

    def __init__(self, connection: Connection, schema: Schema):
        """
        Initialize a Classification class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        schema : weaviate.schema.crud_schema.Schema
            A Schema object instance connected to the same Weaviate instance as the Client.
        """

        self._connection = connection
        self.schema = schema

    def get(
        self,
        class_name: str,
        properties: Union[List[str], str, None] = None,
    ) -> GetBuilder:
        """
        Instantiate a GetBuilder for GraphQL `get` requests.

        Parameters
        ----------
        class_name : str
            Class name of the objects to interact with.
        properties : list of str, str or None
            Properties of the objects to get, by default None. None means `all non-referrence properties` (this happens only if no additional properties are given).

        Returns
        -------
        GetBuilder
            A GetBuilder to make GraphQL `get` requests from weaviate.
        """

        return GetBuilder(class_name, properties, self._connection, self.schema)

    def multi_get(
        self,
        get_builder: List[GetBuilder],
    ) -> MultiGetBuilder:
        """
        Instantiate a MultiGetBuilder for GraphQL `multi_get` requests.
        Bundels multiple get requests into one.

        Parameters
        ----------
        get_builder : list of GetBuilder
            List of GetBuilder objects for a single request each.

        Returns
        -------
        MultiGetBuilder
            A MultiGetBuilder to make GraphQL `get` multiple requests from weaviate.
        """

        return MultiGetBuilder(get_builder, self._connection)

    def aggregate(self, class_name: str) -> AggregateBuilder:
        """
        Instantiate an AggregateBuilder for GraphQL `aggregate` requests.

        Parameters
        ----------
        class_name : str
            Class name of the objects to be aggregated.

        Returns
        -------
        AggregateBuilder
            An AggregateBuilder to make GraphQL `aggregate` requests from weaviate.
        """

        return AggregateBuilder(class_name, self._connection)

    def raw(self, gql_query: str) -> dict:
        """
        Allows to send simple graph QL string queries.
        Be cautious of injection risks when generating query strings.

        Parameters
        ----------
        gql_query : str
            GraphQL query as a string.

        Returns
        -------
        dict
            Data response of the query.

        Examples
        --------
        >>> query = \"""
        ... {
        ...     Get {
        ...         Article(limit: 2) {
        ...         title
        ...         hasAuthors {
        ...             ... on Author {
        ...                 name
        ...                 }
        ...             }
        ...         }
        ...     }
        ... }
        ... \"""
        >>> client.query.raw(query)
        {
        "data": {
            "Get": {
            "Article": [
                {
                "hasAuthors": [
                    {
                    "name": "Jonathan Wilson"
                    }
                ],
                "title": "Sergio Ag\u00fcero has been far more than a great goalscorer for
                            Manchester City"
                },
                {
                "hasAuthors": [
                    {
                    "name": "Emma Elwick-Bates"
                    }
                ],
                "title": "At Swarovski, Giovanna Engelbert Is Crafting Jewels As Exuberantly
                            Joyful As She Is"
                }
            ]
            }
        },
        "errors": null
        }

        Raises
        ------
        TypeError
            If 'gql_query' is not of type str.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(gql_query, str):
            raise TypeError("Query is expected to be a string")

        json_query = {"query": gql_query}

        try:
            response = self._connection.post(path="/graphql", weaviate_object=json_query)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Query not executed.") from conn_err
        if response.status_code == 200:
            return response.json()  # Successfully queried
        raise UnexpectedStatusCodeException("GQL query failed", response)

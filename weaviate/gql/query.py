import sys
from weaviate.connect import REST_METHOD_POST
from weaviate.exceptions import *
from .builder import Builder


class Things:
    """ Proxy class for builder
    """
    def __init__(self, connection):
        self._connection = connection

    def things(self, class_name, properties):
        return Builder(class_name, properties, self._connection)

    def actions(self, class_name, properties):
        return Builder(class_name, properties, self._connection)


class Query:

    def __init__(self, connection):
        """
        :param connection: needed to directly request from builder
        """
        self._connection = connection
        self.get = Things(self._connection)

    def raw(self, gql_query):
        """ Allows to send simple graph QL string queries.
            Be cautious of injection risks when generating query strings.

        :param gql_query: A GQL query in form of a string
        :type gql_query: str
        :return: Data response of the query
        :raises:
            TypeError: If parameter has the wrong type.
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
        """
        if not isinstance(gql_query, str):
            raise TypeError("Query is expected to be a string")

        json_query = {"query": gql_query}

        try:
            response = self._connection.run_rest("/graphql", REST_METHOD_POST, json_query)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, query not executed.'
                                 ).with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()  # Successfully queried
        else:
            raise UnexpectedStatusCodeException("GQL query", response)
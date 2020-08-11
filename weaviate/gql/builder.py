from weaviate.gql.filter import WhereFilter, Explore
from weaviate.connect import REST_METHOD_POST
from weaviate.exceptions import *
import sys


class Builder:

    def __init__(self, class_name, properties, connection):
        """

        :param class_name:
        :type class_name: str
        :param properties:
        :type properties: list of str or str
        """
        self._connection = connection

        if not isinstance(class_name, str):
            raise TypeError(f"class name must be of type str but was {type(class_name)}")
        if not isinstance(properties, (list, str)):
            raise TypeError(f"properties must be of type str or list of str but was {type(properties)}")
        if isinstance(properties, str):
            properties = [properties]

        self._class_name = class_name
        self._properties = properties
        self._where = None  # To store the where filter if it is added
        self._limit = None  # To store the limit filter if it is added
        self._explore = None # To store the explore clause if it is added
        self._contains_filter = False  # true if any filter is added

    def with_where(self, filter):
        """

        :param filter:
        :type filter: dict
        :return:
        """
        self._where = WhereFilter(filter)
        self._contains_filter = True
        return self

    def with_explore(self, explore):
        """

        :param explore:
        :type explore: dict
        :return:
        """
        self._explore = Explore(explore)
        self._contains_filter = True
        return self

    def with_limit(self, limit):
        """

        :param limit:
        :type limit: int
        :return:
        """
        self._limit = limit
        self._contains_filter = True

        return self

    def build(self):
        """
        :return: The gql query as a string
        :rtype: str
        """
        query = f'{{Get{{Things{{{self._class_name}'
        if self._contains_filter:
            query += '('
        if self._where is not None:
            query = query + f'where: {str(self._where)} '
        if self._limit is not None:
            query = query + f'limit: {self._limit} '
        if self._explore is not None:
            query = query + f'explore:{str(self._explore)} '
        if self._contains_filter:
            query += ')'
        query = query + f'{{{" ".join(self._properties)}}}}}}}}}'

        return query

    def do(self):
        query = self.build()

        try:
            response = self._connection.run_rest("/graphql", REST_METHOD_POST, {"query": query})
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err) + ' Connection error, query was not successful.').with_traceback(
                sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()  # success
        else:
            raise UnexpectedStatusCodeException("Query was not successful", response)
import sys
from typing import List, Union, Optional
from weaviate.gql.filter import WhereFilter, Explore
from weaviate.connect import REST_METHOD_POST, Connection
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError


class GetBuilder:
    """
    GetBuilder class used to create GraphQL queries.
    """

    def __init__(self,
            class_name: str,
            properties: Union[List[str], str],
            connection: Connection
        ):
        """
        Initialize a Builder class instance.

        Parameters
        ----------
        class_name : str
            Class name of the objects to interact with.
        properties : list of str or str
            Properties of the objetcs to interact with.
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.

        Raises
        ------
        TypeError
            If argument/s is/are of wrong type.
        """
        self._connection = connection

        if not isinstance(class_name, str):
            raise TypeError(f"class name must be of type str but was {type(class_name)}")
        if not isinstance(properties, (list, str)):
            raise TypeError(f"properties must be of type str or \
                            list of str but was {type(properties)}")
        if isinstance(properties, str):
            properties = [properties]

        self._class_name = class_name
        self._properties = properties
        self._where: Optional[WhereFilter] = None  # To store the where filter if it is added
        self._limit: Optional[int] = None  # To store the limit filter if it is added
        self._explore: Optional[Explore] = None # To store the explore clause if it is added
        self._contains_filter = False  # true if any filter is added

    def with_where(self, filter: dict) -> 'GetBuilder':
        """
        Set 'where' filter.

        Parameters
        ----------
        filter : dict
            The where filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.
        """

        self._where = WhereFilter(filter)
        self._contains_filter = True
        return self

    def with_explore(self, explore: dict) -> 'GetBuilder':
        """
        Set 'explore' filter.

        Parameters
        ----------
        explore : dict
            The explore filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.
        """

        self._explore = Explore(explore)
        self._contains_filter = True
        return self

    def with_limit(self, limit: int) -> 'GetBuilder':
        """
        The limit of objects returned.

        Parameters
        ----------
        limit : dict
            The max number of objects returned.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.
        """

        self._limit = limit
        self._contains_filter = True
        return self

    def build(self) -> str:
        """
        Build query filter as a string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """

        query = f'{{Get{{{self._class_name}'
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
        query = query + f'{{{" ".join(self._properties)}}}}}}}'

        return query

    def do(self) -> dict:
        """
        Builds and runs the query.

        Returns
        -------
        dict
            The response of the query.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        query = self.build()

        try:
            response = self._connection.run_rest("/graphql", REST_METHOD_POST, {"query": query})
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, query was not successful.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])

        if response.status_code == 200:
            return response.json()  # success
        raise UnexpectedStatusCodeException("Query was not successful", response)

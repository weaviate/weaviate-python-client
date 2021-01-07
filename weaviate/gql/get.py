import sys
from typing import List, Union, Optional
from weaviate.gql.filter import WhereFilter, NearText, NearVector
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
        Initialize a GetBuilder class instance.

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
        self._limit: Optional[str] = None  # To store the limit filter if it is added
        self._near_text: Optional[NearText] = None # To store the nearText clause if it is added
        self._near_vector: Optional[NearVector] = None # To store the nearText clause if it is added
        self._contains_filter = False  # true if any filter is added

    def with_where(self, content: dict) -> 'GetBuilder':
        """
        Set `where` filter.

        Parameters
        ----------
        content : dict
            The content of the where filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.
        """

        self._where = WhereFilter(content)
        self._contains_filter = True
        return self

    def with_near_text(self, content: dict) -> 'GetBuilder':
        """
        Set `nearText` filter.

        Parameters
        ----------
        content : dict
            The content of the nearText filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.

        Raises
        ------
        AttributeError
            If 'nearVector' was already set.
        """

        if self._near_vector is not None:
            raise AttributeError("Cannot use both 'nearText' and 'nearVector' filters!")
        self._near_text = NearText(content)
        self._contains_filter = True
        return self

    def with_near_vector(self, vector: list) -> 'GetBuilder':
        """
        Set `nearVector` filter.

        Parameters
        ----------
        vector : list
            The vector of the nearVector filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.

        Raises
        ------
        AttributeError
            If 'nearText' was already set.
        """

        if self._near_text is not None:
            raise AttributeError("Cannot use both 'nearText' and 'nearVector' filters!")
        self._near_vector = NearVector(vector)
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

        Raises
        ------
        ValueError
            If 'limit' is non-positive.
        """

        if limit < 1:
            raise ValueError('limit cannot be negative (limit >=1).')

        self._limit = f'limit: {limit}'
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
                query = query + str(self._where)
            if self._limit is not None:
                query = query + self._limit
            if self._near_vector is not None:
                query = query + str(self._near_vector)
            if self._near_text is not None:
                query = query + str(self._near_text)
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

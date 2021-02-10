"""
GraphQL `Get` command.
"""
from typing import List, Union, Optional
from weaviate.gql.filter import WhereFilter, NearText, NearVector, GraphQL, NearObject, Near
from weaviate.connect import Connection


class GetBuilder(GraphQL):
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

        super().__init__(connection)

        if not isinstance(class_name, str):
            raise TypeError(f"class name must be of type str but was {type(class_name)}")
        if not isinstance(properties, (list, str)):
            raise TypeError("properties must be of type str or "
                f"list of str but was {type(properties)}")
        if isinstance(properties, str):
            properties = [properties]

        self._class_name = class_name
        self._properties = properties
        self._where: Optional[WhereFilter] = None  # To store the where filter if it is added
        self._limit: Optional[str] = None  # To store the limit filter if it is added
        self._near: Optional[Near] = None # To store the `near` clause if it is added
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
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters!")
        self._near = NearText(content)
        self._contains_filter = True
        return self

    def with_near_vector(self, content: dict) -> 'GetBuilder':
        """
        Set `nearVector` filter.

        Parameters
        ----------
        content : dict
            The content of the nearVector filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters!")
        self._near = NearVector(content)
        self._contains_filter = True
        return self

    def with_near_object(self, content: dict) -> 'GetBuilder':
        """
        Set `nearObject` filter.

        Parameters
        ----------
        content : dict
            The content of the nearObject filter to set.

        Returns
        -------
        weaviate.gql.get.GetBuilder
            Updated GetBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters!")
        self._near = NearObject(content)
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
            raise ValueError('limit cannot be non-positive (limit >=1).')

        self._limit = f'limit: {limit} '
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
            if self._near is not None:
                query = query + str(self._near)
            query += ')'
        query = query + f'{{{" ".join(self._properties)}}}}}}}'

        return query

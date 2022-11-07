"""
GraphQL `Aggregate` command.
"""
import json
from typing import List, Optional
from weaviate.connect import Connection
from weaviate.util import _capitalize_first_letter
from .filter import (
    Where,
    GraphQL,
    Filter,
    NearObject,
    NearText,
    NearVector,
)


class AggregateBuilder(GraphQL):
    """
    AggregateBuilder class used to aggregate Weaviate objects.
    """

    def __init__(self, class_name: str, connection: Connection):
        """
        Initialize a AggregateBuilder class instance.

        Parameters
        ----------
        class_name : str
            Class name of the objects to be aggregated.
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.
        """

        super().__init__(connection)
        self._class_name: str = _capitalize_first_letter(class_name)
        self._object_limit: Optional[int] = None
        self._with_meta_count: bool = False
        self._fields: List[str] = []
        self._where: Optional[Where] = None
        self._group_by_properties: Optional[List[str]] = None
        self._uses_filter: bool = False
        self._near: Optional[Filter] = None

    def with_meta_count(self) -> "AggregateBuilder":
        """
        Set Meta Count to True.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._with_meta_count = True
        return self

    def with_object_limit(self, limit: int) -> "AggregateBuilder":
        """
        Set objectLimit to limit vector search results only when with near<MEDIA> filter.

        Parameters
        ----------
        limit : int
            The object limit.

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._object_limit = limit
        return self

    def with_fields(self, field: str) -> "AggregateBuilder":
        """
        Include a field in the aggregate query.

        Parameters
        ----------
        field : str
            Field to include in the aggregate query.
            e.g. '<property_name> { count }'

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._fields.append(field)
        return self

    def with_where(self, content: dict) -> "AggregateBuilder":
        """
        Set 'where' filter.

        Parameters
        ----------
        content : dict
            The where filter to include in the aggregate query. See examples below.

        Examples
        --------
        The `content` prototype is like this:

        >>> content = {
        ...     'operator': '<operator>',
        ...     'operands': [
        ...         {
        ...             'path': [path],
        ...             'operator': '<operator>'
        ...             '<valueType>': <value>
        ...         },
        ...         {
        ...             'path': [<matchPath>],
        ...             'operator': '<operator>',
        ...             '<valueType>': <value>
        ...         }
        ...     ]
        ... }

        This is a complete `where` filter but it does not have to be like this all the time.

        Single operand:

        >>> content = {
        ...     'path': ["wordCount"],    # Path to the property that should be used
        ...     'operator': 'GreaterThan',  # operator
        ...     'valueInt': 1000       # value (which is always = to the type of the path property)
        ... }

        Or

        >>> content = {
        ...     'path': ["id"],
        ...     'operator': 'Equal',
        ...     'valueString': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf"
        ... }

        Multiple operands:

        >>> content = {
        ...     'operator': 'And',
        ...     'operands': [
        ...         {
        ...             'path': ["wordCount"],
        ...             'operator': 'GreaterThan',
        ...             'valueInt': 1000
        ...         },
        ...         {
        ...             'path': ["wordCount"],
        ...             'operator': 'LessThan',
        ...             'valueInt': 1500
        ...         }
        ...     ]
        ... }

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._where = Where(content)
        self._uses_filter = True
        return self

    def with_group_by_filter(self, properties: List[str]) -> "AggregateBuilder":
        """
        Add a group by filter to the query. Might requires the user to set
        an additional group by clause using `with_fields(..)`.

        Parameters
        ----------
        properties : list of str
            list of properties that are included in the group by filter.
            Generates a filter like: 'groupBy: ["property1", "property2"]'
            from a list ["property1", "property2"]

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.
        """

        self._group_by_properties = properties
        self._uses_filter = True
        return self

    def with_near_text(self, content: dict) -> "AggregateBuilder":
        """
        Set `nearText` filter. This filter can be used with text modules (text2vec).
        E.g.: text2vec-contextionary, text2vec-transformers.
        NOTE: The 'autocorrect' field is enabled only with the `text-spellcheck` Weaviate module.

        Parameters
        ----------
        content : dict
            The content of the `nearText` filter to set. See examples below.

        Examples
        --------
        Content full prototype:

        >>> content = {
        ...     'concepts': <list of str or str>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'moveAwayFrom': { # Optional
        ...         'concepts': <list of str or str>,
        ...         'force': <float>
        ...     },
        ...     'moveTo': { # Optional
        ...         'concepts': <list of str or str>,
        ...         'force': <float>
        ...     },
        ...     'autocorrect': <bool>, # Optional
        ... }

        Full content:

        >>> content = {
        ...     'concepts': ["fashion"],
        ...     'certainty': 0.7, # or 'distance' instead
        ...     'moveAwayFrom': {
        ...         'concepts': ["finance"],
        ...         'force': 0.45
        ...     },
        ...     'moveTo': {
        ...         'concepts': ["haute couture"],
        ...         'force': 0.85
        ...     },
        ...     'autocorrect': True
        ... }

        Partial content:

        >>> content = {
        ...     'concepts': ["fashion"],
        ...     'certainty': 0.7, # or 'distance' instead
        ...     'moveTo': {
        ...         'concepts': ["haute couture"],
        ...         'force': 0.85
        ...     }
        ... }

        Minimal content:

        >>> content = {
        ...     'concepts': "fashion"
        ... }

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        self._near = NearText(content)
        self._uses_filter = True
        return self

    def with_near_vector(self, content: dict) -> "AggregateBuilder":
        """
        Set `nearVector` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearVector` filter to set. See examples below.

        Examples
        --------
        Content full prototype:

        >>> content = {
        ...     'vector' : <list of float>,
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        NOTE: Supported types for 'vector' are `list`, 'numpy.ndarray`, `torch.Tensor`
                and `tf.Tensor`.

        Full content:

        >>> content = {
        ...     'vector' : [.1, .2, .3, .5],
        ...     'certainty': 0.75, # or 'distance' instead
        ... }

        Minimal content:

        >>> content = {
        ...     'vector' : [.1, .2, .3, .5]
        ... }

        Or

        >>> content = {
        ...     'vector' : torch.tensor([.1, .2, .3, .5])
        ... }

        Or

        >>> content = {
        ...     'vector' : torch.tensor([[.1, .2, .3, .5]]) # it is going to be squeezed.
        ... }

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        self._near = NearVector(content)
        self._uses_filter = True
        return self

    def with_near_object(self, content: dict) -> "AggregateBuilder":
        """
        Set `nearObject` filter.

        Parameters
        ----------
        content : dict
            The content of the `nearObject` filter to set. See examples below.

        Examples
        --------
        Content prototype:

        >>> content = {
        ...     'id': <str>, # OR 'beacon'
        ...     'beacon': <str>, # OR 'id'
        ...     # certainty ONLY with `cosine` distance specified in the schema
        ...     'certainty': <float>, # Optional, either 'certainty' OR 'distance'
        ...     'distance': <float>, # Optional, either 'certainty' OR 'distance'
        ... }

        >>> {
        ...     'id': "e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf",
        ...     'certainty': 0.7 # or 'distance' instead
        ... }
        >>> # alternatively
        >>> {
        ...     'beacon': "weaviate://localhost/Book/e5dc4a4c-ef0f-3aed-89a3-a73435c6bbcf"
        ...     'certainty': 0.7 # or 'distance' instead
        ... }

        Returns
        -------
        weaviate.gql.aggregate.AggregateBuilder
            Updated AggregateBuilder.

        Raises
        ------
        AttributeError
            If another 'near' filter was already set.
        """

        is_server_version_14 = self._connection.server_version >= "1.14"

        if self._near is not None:
            raise AttributeError("Cannot use multiple 'near' filters.")
        self._near = NearObject(content, is_server_version_14)
        self._uses_filter = True
        return self

    def build(self) -> str:
        """
        Build the query and return the string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """

        # Path
        query = f"{{Aggregate{{{self._class_name}"

        # Filter
        if self._uses_filter:
            query += "("
            if self._where is not None:
                query += str(self._where)
            if self._group_by_properties is not None:
                query += f"groupBy: {json.dumps(self._group_by_properties)}"
            if self._near is not None:
                query += str(self._near)
            if self._object_limit:
                query += f"objectLimit: {self._object_limit}"
            query += ")"

        # Body
        query += "{"
        if self._with_meta_count:
            query += "meta{count}"
        for field in self._fields:
            query += field

        # close
        query += "}}}"
        return query

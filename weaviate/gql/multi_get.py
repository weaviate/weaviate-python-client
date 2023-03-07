"""
GraphQL `Get` command.
"""

from typing import List
from weaviate.gql.filter import (
    GraphQL,
)
from weaviate.connect import Connection
from .get import GetBuilder


class MultiGetBuilder(GraphQL):
    """
    GetBuilder class used to create GraphQL queries.
    """

    def __init__(self, get_builder: List[GetBuilder], connection: Connection):
        """
        Initialize a MultiGetBuilder class instance.

        Parameters
        ----------
        get_builder : list of GetBuilder
            GetBuilder objects for a single request each.
        connection : weaviate.connect.Connection
            Connection object to an active and running Weaviate instance.

        Examples
        --------
        To create a 'multi_get' object using several 'get' request at the same time use:

        >>>    client.query.multi_get(
        ... [
        ...    client.query.get("Ship", ["name"]).with_alias("one"),
        ...    client.query.get("Ship", ["size"]).with_alias("two"),
        ...    client.query.get("Person", ["name"])
        ... ]
        with_alias() needs to be used if the same 'class_name' is used twice during the same 'multi_get' request.

        Raises
        ------
        TypeError
            If 'get_builder' is of wrong type.
        """
        get_names = []
        super().__init__(connection)
        if not isinstance(get_builder, List):
            raise TypeError(f"get_builder must be of type List but was {type(get_builder)}")
        for get in get_builder:
            if not isinstance(get, GetBuilder):
                raise TypeError(
                    f"All objects in 'get_builder' must be of type 'GetBuilder' but at least one object was {type(get)}"
                )
            if get.name not in get_names:
                get_names.append(get.name)
            else:
                raise TypeError(
                    f"Objects in 'get_builder' can not have duplicate names but two were named: '{get.name}'. Queries can be renamed using an alias."
                )
        self.get_builder: List[GetBuilder] = get_builder

    def build(self) -> str:
        """
        Build query filter as a string.

        Returns
        -------
        str
            The GraphQL query as a string.
        """
        query = "{Get{"

        for get in self.get_builder:
            query += get.build(wrap_get=False)
        return query + "}}"

import sys
import json
from weaviate.connect import REST_METHOD_POST
from weaviate.exceptions import UnexpectedStatusCodeException
from .filter import WhereFilter

class AggregateBuilder:

    def __init__(self, class_name, connection, semantic_type):
        self._class_name = class_name
        self._connection = connection
        self._semantic_type = semantic_type
        self._with_meta_count = False
        self._fields = []
        self._where:WhereFilter = None
        self._group_by_properties = None
        self._uses_filter = False

    def with_meta_count(self):
        self._with_meta_count = True
        return self

    def with_fields(self, field):
        """ include a field in the aggregate query

        :param field: e.g. '<property_name> { count }'
        :return:
        :rtype: AggregateBuilder
        """
        self._fields.append(field)
        return self

    def with_where(self, filter):
        self._where = WhereFilter(filter)
        self._uses_filter = True
        return self

    def with_group_by_filter(self, properties):
        """ Add a group by filter to the query.
            Might requires the user to set an additional group by clause using `with_fields(..)`.
        :param properties: list of properties that are included in the group by filter.
                           Generates a filter like: 'groupBy: ["property1", "property2"]'
                           from a list ["property1", "property2"]
        :type properties: list of str
        :return:
        """
        self._group_by_properties = properties
        self._uses_filter = True
        return self

    def build(self):
        """ Build the query and return the string
        """
        # Path
        query = f"{{Aggregate{{{self._semantic_type}{{{self._class_name}"

        # Filter
        if self._uses_filter:
            query += "("
        if self._where is not None:
            query += f"where: {str(self._where)} "
        if self._group_by_properties is not None:
            query += f"groupBy: {json.dumps(self._group_by_properties)}"
        if self._uses_filter:
            query += ")"

        # Body
        query += "{"
        if self._with_meta_count:
            query += "meta{count}"
        for field in self._fields:
            query += field

        # close
        query += "}}}}"
        return query

    def do(self):
        """ Builds and runs the query

        :return: the response of the query
        :rtype: dict
        """
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
import sys
from weaviate import SEMANTIC_TYPE_THINGS
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.schema.validate_schema import check_property
from weaviate.util import is_semantic_type, _get_dict_from_object
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE


class Property:

    def __init__(self, connection):
        """
        :param connection:
        :type connection: weaviate.connect.Connection
        """

        self._connection = connection

    def create(self, schema_class_name, schema_property, semantic_type=SEMANTIC_TYPE_THINGS):
        """

        :param schema_class_name: The name of the class in the schema to which the property should be added
        :type schema_class_name: str
        :param schema_property: The property that should be added
        :type schema_property: dict
        :param semantic_type: Either things or actions.
                              Defaults to things.
                              Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type semantic_type: str
        :return:
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            TypeError: in case of wrong parameter types
            ValueError: in case of wrong parameter value
            SchemaValidationException: in case the property is not valid
        """
        if not isinstance(schema_class_name, str):
            raise TypeError("Class name must be of type str but is", type(schema_class_name))
        if not is_semantic_type(semantic_type):
            raise ValueError("Semantic type must be \"things\" or \"actions\"")
        try:
            loaded_schema_property = _get_dict_from_object(schema_property)
        except ConnectionError:
            raise
        except UnexpectedStatusCodeException:
            raise

        # check if valid property
        check_property(loaded_schema_property)

        path = f"/schema/{semantic_type}/{schema_class_name}/properties"
        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, loaded_schema_property)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, property may not have been created properly.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property to class", response)

    def _delete(self, schema_class_name, schema_property_name, semantic_type=SEMANTIC_TYPE_THINGS):
        """ This function is currently deactivated because it is not available in weaviate yet:
            https://github.com/semi-technologies/weaviate/issues/973

        :param schema_class_name: The class the property that is being removed is a part of.
        :type schema_class_name: str
        :param schema_property_name: The name of the property that should be removed.
        :type schema_property_name: str
        :param semantic_type: Either things or actions.
                              Defaults to things.
                              Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type semantic_type: str
        :return:
        :raises:
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            TypeError: in case of wrong parameter types
            ValueError: in case of wrong parameter value
        """
        if not isinstance(schema_class_name, str):
            raise TypeError("Class name should be str not", type(schema_class_name))
        if not isinstance(schema_property_name, str):
            raise TypeError("Property name should be str not", type(schema_property_name))
        if not is_semantic_type(semantic_type):
            raise ValueError("Semantic type must be \"things\" or \"actions\"")

        path = f"/schema/{semantic_type}/{schema_class_name}/properties/{schema_property_name}"
        try:
            response = self._connection.run_rest(path, REST_METHOD_DELETE)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, property may not have been deleted properly.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Delete property from class", response)


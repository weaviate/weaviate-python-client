import sys
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.schema.validate_schema import check_property
from weaviate.util import _get_dict_from_object
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE, Connection


class Property:
    """
    Property class used to create object properties.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Property class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection

    def create(self, schema_class_name: str, schema_property: dict) -> None:
        """
        Create a class property.

        Parameters
        ----------
        schema_class_name : str
            The name of the class in the schema to which the property
            should be added.
        schema_property : dict
            The property that should be added.

        Raises
        ------
        TypeError
            If 'schema_class_name' is of wrong type.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.SchemaValidationException
            If the 'schema_property' is not valid.
        """

        if not isinstance(schema_class_name, str):
            raise TypeError("Class name must be of type str but is", type(schema_class_name))

        loaded_schema_property = _get_dict_from_object(schema_property)

        # check if valid property
        check_property(loaded_schema_property)

        path = f"/schema/{schema_class_name}/properties"
        try:
            response = self._connection.run_rest(path, REST_METHOD_POST, loaded_schema_property)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, property may not have \
                                        been created properly.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property to class", response)

    def _delete(self, schema_class_name: str, schema_property_name: str) -> None:
        """
        This function is currently deactivated because it is not available in weaviate yet:
        https://github.com/semi-technologies/weaviate/issues/973

        Parameters
        ----------
        schema_class_name : str
            The class the property that is being removed is a part of.
        schema_property_name : str
            The name of the property that should be removed.

        Raises
        ------
        TypeError
            If argument/s is/are of wrong type/s.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.SchemaValidationException
            If the 'schema_property' is not valid.
        """

        if not isinstance(schema_class_name, str):
            raise TypeError("Class name should be str not", type(schema_class_name))
        if not isinstance(schema_property_name, str):
            raise TypeError("Property name should be str not", type(schema_property_name))

        path = f"/schema/{schema_class_name}/properties/{schema_property_name}"
        try:
            response = self._connection.run_rest(path, REST_METHOD_DELETE)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, property may not have \
                                        been deleted properly.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Delete property from class", response)

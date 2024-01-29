"""
Property class definition.
"""

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.util import _get_dict_from_object, _capitalize_first_letter


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

        Examples
        --------
        >>> property_age = {
        ...     "dataType": [
        ...         "int"
        ...     ],
        ...     "description": "The Author's age",
        ...     "name": "age"
        ... }
        >>> client.schema.property.create('Author', property_age)

        Raises
        ------
        TypeError
            If 'schema_class_name' is of wrong type.
        weaviate.exceptions.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.SchemaValidationException
            If the 'schema_property' is not valid.
        """

        if not isinstance(schema_class_name, str):
            raise TypeError(f"Class name must be of type str but is {type(schema_class_name)}")

        loaded_schema_property = _get_dict_from_object(schema_property)

        schema_class_name = _capitalize_first_letter(schema_class_name)

        path = f"/schema/{schema_class_name}/properties"
        try:
            response = self._connection.post(path=path, weaviate_object=loaded_schema_property)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Property was created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property to class", response)

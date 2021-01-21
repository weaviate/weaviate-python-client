import sys
from typing import Union, Optional
from weaviate.connect import Connection, REST_METHOD_POST, REST_METHOD_GET, REST_METHOD_DELETE
from weaviate.util import _get_dict_from_object, _is_sub_schema
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.schema.validate_schema import validate_schema, check_class
from weaviate.schema.properties import Property


_PRIMITIVE_WEAVIATE_TYPES_SET = set(["string", "int", "boolean", "number", "date", "text",\
                                                            "geoCoordinates", "CrossRef"])


class Schema:
    """
    Schema class used to interact and manipulate schemas or classes.
    """

    def __init__(self, connection: Connection):
        """
        Initialize a Schema class instance.

        Parameters
        ----------
        connection : weaviate.connect.Connection
            Connection object to an active and running weaviate instance.
        """

        self._connection = connection
        self.property = Property(self._connection)

    def create(self, schema: Union[dict, str]) -> None:
        """
        Create the schema at the weaviate instance.

        Parameters
        ----------
        schema : dict or str
            Schema as a python dict, or the path to a json file or a url of a json file.

        Raises
            TypeError
                If the 'schema' is neither a string nor a dict.
            ValueError
                If 'schema' can not be converted into a weaviate schema.
            ConnectionError
                If the network connection to weaviate fails.
            UnexpectedStatusCodeException
                If weaviate reports a none OK status.
            SchemaValidationException
                If the 'schema' could not be validated against the standard format.
        """

        loaded_schema = _get_dict_from_object(schema)
        # validate the schema before loading
        validate_schema(loaded_schema)
        self._create_classes_with_primitives(loaded_schema["classes"])
        self._create_complex_properties_from_classes(loaded_schema["classes"])

    def create_class(self, schema_class: Union[dict, str]) -> None:
        """
        Create a single class as part of the schema in weaviate.

        Parameters
        ----------
        schema_class : dict or str
            Class as a python dict, or the path to a json file or a url of a json file.

        Raises
            TypeError
                If the 'schema_class' is neither a string nor a dict.
            ValueError
                If 'schema_class' can not be converted into a weaviate schema.
            ConnectionError
                If the network connection to weaviate fails.
            UnexpectedStatusCodeException
                If weaviate reports a none OK status.
            SchemaValidationException
                If the 'schema_class' could not be validated against the standard format.
        """

        loaded_schema_class = _get_dict_from_object(schema_class)
        # validate the class before loading
        check_class(loaded_schema_class)
        self._create_class_with_premitives(loaded_schema_class)
        self._create_complex_properties_from_class(loaded_schema_class)

    def delete_class(self, class_name: str) -> None:
        """
        Delete a schema class from weaviate. This deletes all associated data.

        Parameters
        ----------
        class_name : str
            The class that should be deleted from weaviate.

        Raises
        ------
        TypeError
            If 'class_name' argument not of type str.
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(class_name, str):
            raise TypeError(f"Class name was {type(class_name)} instead of str")

        path = f"/schema/{class_name}"
        try:
            response = self._connection.run_rest(path, REST_METHOD_DELETE)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, during deletion of class.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Delete class from schema", response)

    def delete_all(self) -> None:
        """
        Remove the entire schema from the weavaite instance and all data associated with it.
        """

        schema = self.get()
        classes = schema.get("classes", [])
        for _class in classes:
            self.delete_class(_class["class"])


    def contains(self, schema: Optional[Union[dict, str]]=None) -> bool:
        """
        Check if weaviate already contains a schema.

        Parameters
        ----------
        schema : dict or str, optional
            Schema as a python dict, or the path to a json file or a url of a json file.
            If a schema is given it is checked if this specific schema is already loaded.
            It will test only this schema. If the given schema is a subset of the loaded
            schema it will still return true, by default None.

        Returns
        -------
        bool
            True if a schema is present,
            False otherwise.
        """

        loaded_schema = self.get()

        if schema is not None:
            sub_schema = _get_dict_from_object(schema)
            return _is_sub_schema(sub_schema, loaded_schema)

        if len(loaded_schema["classes"]) == 0:
            return False
        return True

    def get(self) -> dict:
        """
        Get the schema from weaviate.

        Returns
        -------
        dict
            A dict containing the schema. The schema may be empty.
            To see if a schema has already been loaded use `contains` method.
        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        try:
            response = self._connection.run_rest("/schema", REST_METHOD_GET)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, schema could not be retrieved.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get schema", response)
        return response.json()

    def _create_complex_properties_from_class(self, schema_class: dict) -> None:
        """
        Add crossreferences to already existing class.

        Parameters
        ----------
        schema_class : dict
            Description of the class that should be added.

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if "properties" not in schema_class:
            # Class has no properties nothing to do
            return
        for property_ in schema_class["properties"]:

            if _property_is_primitive(property_["dataType"]):
                continue
            # create the property object
            schema_property = {
                "dataType": property_["dataType"],
                "description": property_["description"],
                "name": property_["name"]
            }

            if "indexInverted" in property_:
                schema_property["indexInverted"] = property_["indexInverted"]

            if "moduleConfig" in property_:
                schema_property["moduleConfig"] = property_["moduleConfig"]

            path = "/schema/" + schema_class["class"] + "/properties"
            try:
                response = self._connection.run_rest(path, REST_METHOD_POST, schema_property)
            except RequestsConnectionError as conn_err:
                message = str(conn_err)\
                        + ' Connection error, property may not have been created properly.'
                raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Add properties to classes", response)

    def _create_complex_properties_from_classes(self, schema_classes_list: list) -> None:
        """
        Add crossreferences to already existing classes.

        Parameters
        ----------
        schema_classes_list : list
            A list of classes as they are found in a schema json description.
        """

        for schema_class in schema_classes_list:
            self._create_complex_properties_from_class(schema_class)

    def _create_class_with_premitives(self, weaviate_class: dict) -> None:
        """
        Create class with only primitives.

        Parameters
        ----------
        weaviate_class : dict
            A single weaviate formated class

        Raises
        ------
        requests.exceptions.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        # Create the class
        schema_class = {
            "class": weaviate_class['class'],
            "properties": []
        }

        if "description" in weaviate_class:
            schema_class['description'] = weaviate_class['description']

        if "vectorIndexType" in weaviate_class:
            schema_class['vectorIndexType'] = weaviate_class['vectorIndexType']

        if "vectorIndexConfig" in weaviate_class:
            schema_class['vectorIndexConfig'] = weaviate_class['vectorIndexConfig']

        if "vectorizer" in weaviate_class:
            schema_class['vectorizer'] = weaviate_class['vectorizer']

        if "moduleConfig" in weaviate_class:
            schema_class["moduleConfig"] = weaviate_class["moduleConfig"]

        if "properties" in weaviate_class:
            schema_class["properties"] = _get_primitive_properties(
                                                    weaviate_class["properties"])

        # Add the item
        try:
            response = self._connection.run_rest("/schema", REST_METHOD_POST, schema_class)
        except RequestsConnectionError as conn_err:
            message = str(conn_err) + ' Connection error, class may not have been created properly.'
            raise type(conn_err)(message).with_traceback(sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)

    def _create_classes_with_primitives(self, schema_classes_list: list) -> None:
        """
        Create all the classes in the list and primitive properties.
        This function does not create references,
        to avoid references to classes that do not yet exist.

        Parameters
        ----------
        schema_classes_list : list
            A list of classes as they are found in a schema json description.
        """

        for weaviate_class in schema_classes_list:
            self._create_class_with_premitives(weaviate_class)


def _property_is_primitive(data_type_list: list) -> bool:
    """
    Check if the property is primitive.

    Parameters
    ----------
    data_type_list : list
        Data types to be checkedif are primitive.

    Returns
    -------
    bool
        True if it only consists of primitive data types,
        False otherwise.
    """

    if len(set(data_type_list) - _PRIMITIVE_WEAVIATE_TYPES_SET) == 0:
        return True
    return False


def _get_primitive_properties(properties_list: list) -> list:
    """
    Filter the list of properties for only primitive properties.

    Parameters
    ----------
    properties_list : list
        A list of properties to exctract the primitive properties.

    Returns
    -------
    list
        A list of properties containing only primitives.
    """

    primitive_properties = []
    for property_ in properties_list:
        if not _property_is_primitive(property_["dataType"]):
            # property is complex and therefore will be ignored
            continue
        primitive_properties.append(property_)
    return primitive_properties

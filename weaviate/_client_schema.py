import sys

from .connect import *
from .exceptions import *
from .util import _get_dict_from_object, _is_sub_schema
from .validate_schema import validate_schema
from requests.exceptions import ConnectionError
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS

# This file contains all methods of the client to handle the weaviate schema

_PRIMITIVE_WEAVIATE_TYPES = ["string", "int", "boolean", "number", "date", "text", "geoCoordinates", "CrossRef"]


def create_schema(self, schema):
    """ Create the schema at the weaviate instance.

    :param schema: can either be the path to a json file, a url of a json file or a python native dict.
    :type schema: str, dict
    :return: None if successful.
    :raises:
        TypeError: if the schema is neither a string nor a dict.
        ValueError: if schema can not be converted into a weaviate schema.
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
        SchemaValidationException: if the schema could not be validated against the standard format.
    """
    try:
        loaded_schema = _get_dict_from_object(schema)
    except ConnectionError:
        raise
    except UnexpectedStatusCodeException:
        raise

    # validate the schema before loading
    validate_schema(loaded_schema)

    if SEMANTIC_TYPE_THINGS in loaded_schema:
        self._create_class_with_primitives(SEMANTIC_TYPE_THINGS,
                                           loaded_schema[SEMANTIC_TYPE_THINGS]["classes"])
    if SEMANTIC_TYPE_ACTIONS in loaded_schema:
        self._create_class_with_primitives(SEMANTIC_TYPE_ACTIONS,
                                           loaded_schema[SEMANTIC_TYPE_ACTIONS]["classes"])
    if SEMANTIC_TYPE_THINGS in loaded_schema:
        self._create_complex_properties(SEMANTIC_TYPE_THINGS,
                                        loaded_schema[SEMANTIC_TYPE_THINGS]["classes"])
    if SEMANTIC_TYPE_ACTIONS in loaded_schema:
        self._create_complex_properties(SEMANTIC_TYPE_ACTIONS,
                                        loaded_schema[SEMANTIC_TYPE_ACTIONS]["classes"])


def contains_schema(self, schema=None):
    """ To check if weaviate already contains a schema.

    :param schema: if a schema is given it is checked if this
        specific schema is already loaded. It will test only this schema.
        If the given schema is a subset of the loaded schema it will still return true.
    :return: True if a schema is present otherwise False
    :rtype: bool
    :raises:
        ConnectionError: In case of network issues.
    """
    loaded_schema = self.get_schema()

    if schema is not None:
        return _is_sub_schema(schema, loaded_schema)

    if len(loaded_schema["things"]["classes"]) > 0 or len(loaded_schema["actions"]["classes"]) > 0:
        return True

    return False


def get_schema(self):
    """ Get the schema in weaviate

    :return: a dict containing the schema.
             The schema may be empty. To see if a schema has already been loaded use contains_schema.
    :raises:
        ConnectionError: In case of network issues.
    """
    try:
        response = self._connection.run_rest("/schema", REST_METHOD_GET)
    except ConnectionError as conn_err:
        raise type(conn_err)(str(conn_err)
                             + ' Connection error, schema could not be retrieved.'
                             ).with_traceback(
            sys.exc_info()[2])
    if response.status_code == 200:
        return response.json()
    else:
        raise UnexpectedStatusCodeException("Get schema", response)


def _create_complex_properties(self, semantic_type, schema_classes_list):
    """ Add crossreferences to already existing classes

    :param semantic_type: can be found as constants e.g. SEMANTIC_TYPE_THINGS.
    :type semantic_type: SEMANTIC_TYPE_THINGS or SEMANTIC_TYPE_ACTIONS
    :param schema_classes_list: classes as they are found in a schema json description.
    :type schema_classes_list: list
    :return: None if successful.
    :raises
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """

    for schema_class in schema_classes_list:
        for property_ in schema_class["properties"]:

            if self._property_is_primitive(property_["dataType"]):
                continue

            # create the property object
            schema_property = {
                "dataType": property_["dataType"],
                "cardinality": property_["cardinality"],
                "description": property_["description"],
                "name": property_["name"]
            }

            if "index" in property_:
                schema_property["index"] = property_["index"]
            if "vectorizePropertyName" in property_:
                schema_property["vectorizePropertyName"] = property_["vectorizePropertyName"]

            # add keywords
            if "keywords" in property_:
                schema_property["keywords"] = property_["keywords"]

            path = "/schema/" + semantic_type + "/" + schema_class["class"] + "/properties"
            try:
                response = self._connection.run_rest(path, REST_METHOD_POST, schema_property)
            except ConnectionError as conn_err:
                raise type(conn_err)(str(conn_err)
                                     + ' Connection error, property may not have been created properly.'
                                     ).with_traceback(
                    sys.exc_info()[2])
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Add properties to classes", response)


def _property_is_primitive(self, data_type_list):
    """ Checks if the property is primitive

    :param data_type_list: Data types of the property
    :type data_type_list: list
    :return: true if it only consists of primitive types
    """
    for data_type in data_type_list:
        if data_type not in _PRIMITIVE_WEAVIATE_TYPES:
            return False
    return True


def _get_primitive_properties(self, properties_list):
    """ Filters the list of properties for only primitive properties

    :param properties_list: A list of schema properties
    :type properties_list: list
    :return: a list of properties containing only primitives or an empty list
    """
    primitive_properties = []

    for property_ in properties_list:

        if not self._property_is_primitive(property_["dataType"]):
            # property is complex and therefore will be ignored
            continue

        # create the property object
        schema_property = {
            "dataType": property_["dataType"],
            "description": property_["description"],
            "name": property_["name"]
        }

        # Check not mandetory fields
        if "index" in property_:
            schema_property["index"] = property_["index"]
        if "vectorizePropertyName" in property_:
            schema_property["vectorizePropertyName"] = property_["vectorizePropertyName"]
        if "cardinality" in property_:
            schema_property["cardinality"] = property_["cardinality"]

        # add keywords
        if "keywords" in property_:
            schema_property["keywords"] = property_["keywords"]

        primitive_properties.append(schema_property)

    return primitive_properties


def _create_class_with_primitives(self, semantic_type, schema_classes_list):
    """ Create all the classes in the list and primitive properties.
    This function does not create references,
    to avoid references to classes that do not yet exist.

    :param semantic_type: can be found as constants e.g. SEMANTIC_TYPE_THINGS.
    :type semantic_type: SEMANTIC_TYPE_THINGS or SEMANTIC_TYPE_ACTIONS
    :param schema_classes_list: classes as they are found in a schema json description.
    :type schema_classes_list: list
    :return: None if successful.
    :raises
        ConnectionError: if the network connection to weaviate fails.
        UnexpectedStatusCodeException: if weaviate reports a none OK status.
    """

    for weaviate_class in schema_classes_list:

        # Create the class
        schema_class = {
            "class": weaviate_class['class'],
            "description": weaviate_class['description'],
            "properties": [],
            "keywords": []
        }

        if "vectorizeClassName" in weaviate_class:
            schema_class["vectorizeClassName"] = weaviate_class["vectorizeClassName"]

        if "properties" in weaviate_class:
            schema_class["properties"] = self._get_primitive_properties(weaviate_class["properties"])

        # Add the item
        try:
            response = self._connection.run_rest("/schema/" + semantic_type, REST_METHOD_POST, schema_class)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, class may not have been created properly.').with_traceback(
                sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Create class", response)
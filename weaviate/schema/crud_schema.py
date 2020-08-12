import sys
from weaviate.connect import *
from weaviate.util import _get_dict_from_object, _is_sub_schema, is_semantic_type
from weaviate.exceptions import *
from weaviate.schema.validate_schema import validate_schema, check_class
from weaviate import SEMANTIC_TYPE_ACTIONS, SEMANTIC_TYPE_THINGS

_PRIMITIVE_WEAVIATE_TYPES = ["string", "int", "boolean", "number", "date", "text", "geoCoordinates", "CrossRef"]


class Schema:

    def __init__(self, connection):
        """

        :param connection:
        :type connection: weaviate.connect.Connection
        """
        self._connection = connection

    def create(self, schema):
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
            self._create_classes_with_primitives(SEMANTIC_TYPE_THINGS,
                                                 loaded_schema[SEMANTIC_TYPE_THINGS]["classes"])
        if SEMANTIC_TYPE_ACTIONS in loaded_schema:
            self._create_classes_with_primitives(SEMANTIC_TYPE_ACTIONS,
                                                 loaded_schema[SEMANTIC_TYPE_ACTIONS]["classes"])
        if SEMANTIC_TYPE_THINGS in loaded_schema:
            self._create_complex_properties_from_classes(SEMANTIC_TYPE_THINGS,
                                                         loaded_schema[SEMANTIC_TYPE_THINGS]["classes"])
        if SEMANTIC_TYPE_ACTIONS in loaded_schema:
            self._create_complex_properties_from_classes(SEMANTIC_TYPE_ACTIONS,
                                                         loaded_schema[SEMANTIC_TYPE_ACTIONS]["classes"])

    def create_class(self, schema_class, semantic_type=SEMANTIC_TYPE_THINGS):
        """ Creates a single class as part of the schema in weaviate.

        :param schema_class: Description of the class that should be added
        :type schema_class: dict
        :param semantic_type: Either things or actions.
                              Defaults to things.
                              Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type semantic_type: str
        :return: None if successful
        """
        check_class(schema_class)
        self._create_class_with_premitives(semantic_type, schema_class)
        self._create_complex_properties_from_class(schema_class, semantic_type)

    def delete_class(self, class_name, semantic_type=SEMANTIC_TYPE_THINGS):
        """ Delete a schema class from weaviate. This deletes all associated data.

        :param class_name: that should be deleted
        :type class_name: str
        :param semantic_type: Either things or actions.
                          Defaults to things.
                          Settable through the constants SEMANTIC_TYPE_THINGS and SEMANTIC_TYPE_ACTIONS
        :type semantic_type: str
        :return: None
        :raises
            ConnectionError: if the network connection to weaviate fails.
            UnexpectedStatusCodeException: if weaviate reports a none OK status.
            TypeError: if parameters are wrong type
        """
        if not isinstance(class_name, str):
            raise TypeError(f"Class name was {type(class_name)} instead of str")
        if not is_semantic_type(semantic_type):
            raise ValueError("Semantic type must be \"things\" or \"actions\"")

        path = f"/schema/{semantic_type}/{class_name}"
        try:
            response = self._connection.run_rest(path, REST_METHOD_DELETE)
        except ConnectionError as conn_err:
            raise type(conn_err)(str(conn_err)
                                 + ' Connection error, during deletion of class.'
                                 ).with_traceback(
                sys.exc_info()[2])
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Delete class from schema", response)

    def delete_all(self):
        """ Removes the entire schema from the weavaite instance and all data associated with it.

        :return: None
        """
        schema = self.get()
        self._delete_all_classes_of_type(SEMANTIC_TYPE_THINGS, schema)
        self._delete_all_classes_of_type(SEMANTIC_TYPE_ACTIONS, schema)

    def _delete_all_classes_of_type(self, semantic_type, schema):
        classes = schema.get(semantic_type, {}).get("classes", [])
        for _class in classes:
            self.delete_class(_class["class"], semantic_type)

    def contains(self, schema=None):
        """ To check if weaviate already contains a schema.

        :param schema: if a schema is given it is checked if this
            specific schema is already loaded. It will test only this schema.
            If the given schema is a subset of the loaded schema it will still return true.
        :return: True if a schema is present otherwise False
        :rtype: bool
        :raises:
            ConnectionError: In case of network issues.
        """
        loaded_schema = self.get()

        if schema is not None:
            return _is_sub_schema(schema, loaded_schema)

        if len(loaded_schema["things"]["classes"]) > 0 or len(loaded_schema["actions"]["classes"]) > 0:
            return True

        return False

    def get(self):
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

    def _create_complex_properties_from_class(self, schema_class, semantic_type):
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

    def _create_complex_properties_from_classes(self, semantic_type, schema_classes_list):
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
            self._create_complex_properties_from_class(schema_class, semantic_type)


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

    def _create_class_with_premitives(self, semantic_type, weaviate_class):
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

    def _create_classes_with_primitives(self, semantic_type, schema_classes_list):
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
            self._create_class_with_premitives(semantic_type, weaviate_class)

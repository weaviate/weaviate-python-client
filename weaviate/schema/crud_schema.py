"""
Schema class definition.
"""
from typing import Union, Optional
from weaviate.connect import Connection
from weaviate.util import _get_dict_from_object, _is_sub_schema
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.schema.validate_schema import validate_schema, check_class
from weaviate.schema.properties import Property


_PRIMITIVE_WEAVIATE_TYPES_SET = set(
    [
        "string",
        "string[]",
        "int",
        "int[]",
        "boolean",
        "number",
        "number[]",
        "date",
        "text",
        "text[]",
        "geoCoordinates",
        "blob",
        "phoneNumber"
    ]
)


class Schema:
    """
    Schema class used to interact and manipulate schemas or classes.

    Attributes
    ----------
    property : weaviate.schema.properties.Property
        A Property object to create new schema property/ies.
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

        Examples
        --------
        >>> author_class_schema = {
        ...     "class": "Author",
        ...     "description": "An Author class to store the author information",
        ...     "properties": [
        ...         {
        ...             "name": "name",
        ...             "dataType": ["string"],
        ...             "description": "The name of the author",
        ...         },
        ...         {
        ...             "name": "wroteArticles",
        ...             "dataType": ["Article"],
        ...             "description": "The articles of the author",
        ...         }
        ...     ]
        ... }
        >>> client.schema.create(author_class_schema)

        If you have your schema saved in the './schema/my_schema.json' you can create it
        directly from the file.

        >>> client.schema.create('./schema/my_schema.json')

        Raises
        ------
        TypeError
            If the 'schema' is neither a string nor a dict.
        ValueError
            If 'schema' can not be converted into a weaviate schema.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        weaviate.SchemaValidationException
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

        Examples
        --------
        >>> author_class_schema = {
        ...     "class": "Author",
        ...     "description": "An Author class to store the author information",
        ...     "properties": [
        ...         {
        ...             "name": "name",
        ...             "dataType": ["string"],
        ...             "description": "The name of the author",
        ...         },
        ...         {
        ...             "name": "wroteArticles",
        ...             "dataType": ["Article"],
        ...             "description": "The articles of the author",
        ...         }
        ...     ]
        ... }
        >>> client.schema.create_class(author_class_schema)

        If you have your class schema saved in the './schema/my_schema.json' you can create it
        directly from the file.

        >>> client.schema.create_class('./schema/my_schema.json')

        Raises
        ------
        TypeError
            If the 'schema_class' is neither a string nor a dict.
        ValueError
            If 'schema_class' can not be converted into a weaviate schema.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        weaviate.SchemaValidationException
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

        Examples
        --------
        >>> client.schema.delete_class('Author')

        Raises
        ------
        TypeError
            If 'class_name' argument not of type str.
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        if not isinstance(class_name, str):
            raise TypeError(f"Class name was {type(class_name)} instead of str")

        path = f"/schema/{class_name}"
        try:
            response = self._connection.delete(
                path=path
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Deletion of class.') from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Delete class from schema", response)

    def delete_all(self) -> None:
        """
        Remove the entire schema from the Weaviate instance and all data associated with it.

        Examples
        --------
        >>> client.schema.delete_all()
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

        Examples
        --------
        >>> schema = client.schema.get()
        >>> client.schema.contains(schema)
        True
        >>> schema = client.schema.get()
        >>> schema['classes'].append(
            {
                "class": "Animal",
                "description": "An Animal",
                "properties": [
                    {
                        "name": "type",
                        "dataType": ["string"],
                        "description": "The animal type",
                    }
                ]
            }
        )
        >>> client.schema.contains(schema)
        False

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

    def update_config(self, class_name: str, config: dict) -> None:
        """
        Update a schema configuration for a specific class.

        Parameters
        ----------
        class_name : str
            The class for which to update the schema configuration.
        config : dict
            The configurations to update (MUST follow schema format).

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        class_schema = self.get(class_name)
        new_class_schema = _update_nested_dict(class_schema, config)
        check_class(new_class_schema)

        path = "/schema/" + class_name
        try:
            response = self._connection.put(
                path=path,
                weaviate_object=new_class_schema
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Class schema configuration could not be updated.')\
                from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Update class schema configuration", response)


    def get(self, class_name: str = None) -> dict:
        """
        Get the schema from weaviate.

        Parameters
        ----------
        class_name : str, optional
            The class for which to return the schema. If NOT provided the whole schema is returned,
            otherwise only the schema of this class is returned. By default None.

        Returns
        -------
        dict
            A dict containing the schema. The schema may be empty.
            To see if a schema has already been loaded use `contains` method.

        Examples
        --------
        No schema present in client

        >>> client.schema.get()
        {'classes': []}

        Schema present in client

        >>> client.schema.get()
        {
            "classes": [
                {
                "class": "Animal",
                "description": "An Animal",
                "invertedIndexConfig": {
                    "cleanupIntervalSeconds": 60
                },
                "properties": [
                    {
                    "dataType": [
                        "string"
                    ],
                    "description": "The animal type",
                    "name": "type"
                    }
                ],
                "vectorIndexConfig": {
                    "cleanupIntervalSeconds": 300,
                    "maxConnections": 64,
                    "efConstruction": 128,
                    "vectorCacheMaxObjects": 500000
                },
                "vectorIndexType": "hnsw",
                "vectorizer": "text2vec-contextionary"
                }
            ]
        }

        >>> client.schema.get('Animal')
        {
            "class": "Animal",
            "description": "An Animal",
            "invertedIndexConfig": {
                "cleanupIntervalSeconds": 60
            },
            "properties": [
                {
                "dataType": [
                    "string"
                ],
                "description": "The animal type",
                "name": "type"
                }
            ],
            "vectorIndexConfig": {
                "cleanupIntervalSeconds": 300,
                "maxConnections": 64,
                "efConstruction": 128,
                "vectorCacheMaxObjects": 500000
            },
            "vectorIndexType": "hnsw",
            "vectorizer": "text2vec-contextionary"
        }

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        path = '/schema'
        if class_name is not None:
            if not isinstance(class_name, str):
                raise TypeError("'class_name' argument must be of type `str`! "
                    f"Given type: {type(class_name)}")
            path = f'/schema/{class_name}'

        try:
            response = self._connection.get(
                path=path
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Schema could not be retrieved.') from conn_err
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
        requests.ConnectionError
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
                response = self._connection.post(
                    path=path,
                   weaviate_object=schema_property
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError('Property may not have been created properly.')\
                    from conn_err
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
        requests.ConnectionError
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

        if "shardingConfig" in weaviate_class:
            schema_class["shardingConfig"] = weaviate_class["shardingConfig"]

        if "properties" in weaviate_class:
            schema_class["properties"] = _get_primitive_properties(
                                                    weaviate_class["properties"])

        # Add the item
        try:
            response = self._connection.post(
                path="/schema",
                weaviate_object=schema_class
            )
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError('Class may not have been created properly.')\
                from conn_err
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
        Data types to be checked if are primitive.

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


def _update_nested_dict(dict_1: dict, dict_2: dict) -> dict:
    """
    Update `dict_1` with elements from `dict_2` in a nested manner.
    If a value of a key is a dict, it is going to be updated and not replaced by a the whole dict.

    Parameters
    ----------
    dict_1 : dict
        The dictionary to be updated.
    dict_2 : dict
        The dictionary that contains values to be updated.

    Returns
    -------
    dict
        The updated `dict_1`.
    """
    for key, value in dict_2.items():
        if key not in dict_1:
            dict_1[key] = value
            continue
        if isinstance(value, dict):
            _update_nested_dict(dict_1[key], value)
        else:
            dict_1.update({key : value})
    return dict_1

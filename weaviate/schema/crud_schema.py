"""
Schema class definition.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Union, Optional, List, Dict, cast

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.connect import Connection
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.schema.properties import Property
from weaviate.util import (
    _get_dict_from_object,
    _is_sub_schema,
    _capitalize_first_letter,
    _decode_json_response_dict,
    _decode_json_response_list,
)

CLASS_KEYS = {
    "class",
    "vectorIndexType",
    "vectorIndexConfig",
    "moduleConfig",
    "description",
    "vectorizer",
    "properties",
    "invertedIndexConfig",
    "shardingConfig",
    "replicationConfig",
    "multiTenancyConfig",
}

PROPERTY_KEYS = {
    "dataType",
    "name",
    "moduleConfig",
    "description",
    "indexInverted",
    "tokenization",
    "indexFilterable",
    "indexSearchable",
}

_PRIMITIVE_WEAVIATE_TYPES_SET = {
    "string",
    "string[]",
    "int",
    "int[]",
    "boolean",
    "boolean[]",
    "number",
    "number[]",
    "date",
    "date[]",
    "text",
    "text[]",
    "geoCoordinates",
    "blob",
    "phoneNumber",
    "uuid",
    "uuid[]",
}


class TenantActivityStatus(str, Enum):
    """
    TenantActivityStatus class used to describe the activity status of a tenant in Weaviate.

    Attributes
    ----------
    HOT: The tenant is fully active and can be used.
    COLD: The tenant is not active, files stored locally.
    """

    HOT = "HOT"
    COLD = "COLD"


@dataclass
class Tenant:
    """
    Tenant class used to describe a tenant in Weaviate.

    Attributes
    ----------
    activity_status : TenantActivityStatus, optional
        default: "HOT"
    name: the name of the tenant.
    """

    name: str
    activity_status: TenantActivityStatus = TenantActivityStatus.HOT

    def _to_weaviate_object(self) -> Dict[str, str]:
        return {
            "activityStatus": self.activity_status,
            "name": self.name,
        }

    @classmethod
    def _from_weaviate_object(cls, weaviate_object: Dict[str, str]) -> "Tenant":
        return cls(
            name=weaviate_object["name"],
            activity_status=TenantActivityStatus(weaviate_object.get("activityStatus", "HOT")),
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
            Connection object to an active and running Weaviate instance.
        """

        self._connection = connection
        self.property = Property(self._connection)

    def create(self, schema: Union[dict, str]) -> None:
        """
        Create the schema of the Weaviate instance, with all classes at once.

        Parameters
        ----------
        schema : dict or str
            Schema as a Python dict, or the path to a JSON file, or the URL of a JSON file.

        Examples
        --------
        >>> article_class = {
        ...     "class": "Article",
        ...     "description": "An article written by an Author",
        ...     "properties": [
        ...         {
        ...             "name": "title",
        ...             "dataType": ["text"],
        ...             "description": "The title the article",
        ...         },
        ...         {
        ...             "name": "hasAuthors",
        ...             "dataType": ["Author"],
        ...             "description": "Authors this article has",
        ...         }
        ...     ]
        ... }
        >>> author_class = {
        ...     "class": "Author",
        ...     "description": "An Author class to store the author information",
        ...     "properties": [
        ...         {
        ...             "name": "name",
        ...             "dataType": ["text"],
        ...             "description": "The name of the author",
        ...         },
        ...         {
        ...             "name": "wroteArticles",
        ...             "dataType": ["Article"],
        ...             "description": "The articles of the author",
        ...         }
        ...     ]
        ... }
        >>> client.schema.create({"classes": [article_class, author_class]})

        If you have your schema saved in the './schema/my_schema.json' you can create it
        directly from the file.

        >>> client.schema.create('./schema/my_schema.json')

        Raises
        ------
        TypeError
            If the 'schema' is neither a string nor a dict.
        ValueError
            If 'schema' can not be converted into a Weaviate schema.
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        weaviate.SchemaValidationException
            If the 'schema' could not be validated against the standard format.
        """

        loaded_schema = _get_dict_from_object(schema)
        self._create_classes_with_primitives(loaded_schema["classes"])
        self._create_complex_properties_from_classes(loaded_schema["classes"])

    def create_class(self, schema_class: Union[dict, str]) -> None:
        """
        Create a single class as part of the schema in Weaviate.

        Parameters
        ----------
        schema_class : dict or str
            Class as a Python dict, or the path to a JSON file, or the URL of a JSON file.

        Examples
        --------
        >>> author_class_schema = {
        ...     "class": "Author",
        ...     "description": "An Author class to store the author information",
        ...     "properties": [
        ...         {
        ...             "name": "name",
        ...             "dataType": ["text"],
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
            If 'schema_class' can not be converted into a Weaviate schema.
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        weaviate.SchemaValidationException
            If the 'schema_class' could not be validated against the standard format.
        """

        loaded_schema_class = _get_dict_from_object(schema_class)
        self._create_class_with_primitives(loaded_schema_class)
        self._create_complex_properties_from_class(loaded_schema_class)

    def delete_class(self, class_name: str) -> None:
        """
        Delete a schema class from Weaviate. This deletes all associated data.

        Parameters
        ----------
        class_name : str
            The class that should be deleted from Weaviate.

        Examples
        --------
        >>> client.schema.delete_class('Author')

        Raises
        ------
        TypeError
            If 'class_name' argument not of type str.
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        if not isinstance(class_name, str):
            raise TypeError(f"Class name was {type(class_name)} instead of str")

        path = f"/schema/{_capitalize_first_letter(class_name)}"
        try:
            response = self._connection.delete(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Deletion of class.") from conn_err
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

    def exists(self, class_name: str) -> bool:
        """
        Check if class exists in Weaviate.

        Parameters
        ----------
        class_name : str
            The class whose existence is being checked.

        Examples
        --------
        >>> client.schema.exists(class_name="Exists")
        True

        >>> client.schema.exists(class_name="DoesNotExists")
        False

        Returns
        -------
        bool
            True if the class exists,
            False otherwise.
        """

        if not isinstance(class_name, str):
            raise TypeError(
                f"'class_name' argument must be of type `str`! Given type: {type(class_name)}."
            )

        path = f"/schema/{_capitalize_first_letter(class_name)}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Checking class existence could not be done."
            ) from conn_err
        if response.status_code == 200:
            return True
        elif response.status_code == 404:
            return False

        raise UnexpectedStatusCodeException("Check if class exists", response)

    def contains(self, schema: Optional[Union[dict, str]] = None) -> bool:
        """
        Check if Weaviate already contains a schema.

        Parameters
        ----------
        schema : dict or str, optional
            Schema as a Python dict, or the path to a JSON file or the URL of a JSON file.
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
                        "dataType": ["text"],
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

        Example
        -------
        In the example below we have a Weaviate instance with a class 'Test'.

        >>> client.schema.get('Test')
        {
            'class': 'Test',
            ...
            'vectorIndexConfig': {
                'ef': -1,
                ...
            },
            ...
        }
        >>> client.schema.update_config(
        ...     class_name='Test',
        ...     config={
        ...         'vectorIndexConfig': {
        ...             'ef': 100,
        ...         }
        ...     }
        ... )
        >>> client.schema.get('Test')
        {
            'class': 'Test',
            ...
            'vectorIndexConfig': {
                'ef': 100,
                ...
            },
            ...
        }

        NOTE: When updating schema configuration, the 'config' MUST be sub-set of the schema,
        starting at the top level. In the example above we update 'ef' value, and for this we
        included the 'vectorIndexConfig' top level too.

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        class_name = _capitalize_first_letter(class_name)
        class_schema = self.get(class_name)
        new_class_schema = _update_nested_dict(class_schema, config)

        path = "/schema/" + class_name
        try:
            response = self._connection.put(path=path, weaviate_object=new_class_schema)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Class schema configuration could not be updated."
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Update class schema configuration", response)

    def get(self, class_name: Optional[str] = None) -> dict:
        """
        Get the schema from Weaviate.

        Parameters
        ----------
        class_name : str, optional
            The class for which to return the schema. If NOT provided the whole schema is returned,
            otherwise only the schema of this class is returned. By default None.

        Returns
        -------
        dict
            A dict containing the schema. The schema may be empty.
            To see if a schema has already been loaded, use the `contains` method.

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
                    "dataType": ["text"],
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
                "vectorizer": "text2vec-contextionary",
                "replicationConfig": {
                    "factor": 1
                }
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
                "dataType": ["text"],
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
            "vectorizer": "text2vec-contextionary",
            "replicationConfig": {
                "factor": 1
            }
        }

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        path = "/schema"
        if class_name is not None:
            if not isinstance(class_name, str):
                raise TypeError(
                    "'class_name' argument must be of type `str`! "
                    f"Given type: {type(class_name)}"
                )
            path = f"/schema/{_capitalize_first_letter(class_name)}"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Schema could not be retrieved.") from conn_err

        res = _decode_json_response_dict(response, "Get schema")
        assert res is not None
        return res

    def get_class_shards(self, class_name: str) -> list:
        """
        Get the status of all shards in an index.

        Parameters
        ----------
        class_name : str
            The class for which to return the status of all shards in an index.

        Returns
        -------
        list
            The list of shards configuration.

        Examples
        --------
        Schema contains a single class: Article

        >>> client.schema.get_class_shards('Article')
        [{'name': '2rPgsA2yngW3', 'status': 'READY'}]

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        if not isinstance(class_name, str):
            raise TypeError(
                "'class_name' argument must be of type `str`! " f"Given type: {type(class_name)}."
            )
        path = f"/schema/{_capitalize_first_letter(class_name)}/shards"

        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Class shards' status could not be retrieved due to connection error."
            ) from conn_err

        res = _decode_json_response_list(response, "Get shards' status")
        assert res is not None
        return res

    def update_class_shard(
        self,
        class_name: str,
        status: str,
        shard_name: Optional[str] = None,
    ) -> list:
        """
        Get the status of all shards in an index.

        Parameters
        ----------
        class_name : str
            The class for which to update the status of all shards in an index.
        status : str
            The new status of the shard. The available options are: 'READY' and 'READONLY'.
        shard_name : str or None, optional
            The shard name for which to update the status of the class of the shard. If None then
            all the shards are going to be updated to the 'status'. By default None.

        Returns
        -------
        list
            The updated statuses.

        Examples
        --------
        Schema contains a single class: Article

        >>> client.schema.get_class_shards('Article')
        [{'name': 'node1', 'status': 'READY'}, {'name': 'node2', 'status': 'READY'}]

        For a specific shard:

        >>> client.schema.update_class_shard('Article', 'READONLY', 'node2')
        {'status': 'READONLY'}
        >>> client.schema.get_class_shards('Article')
        [{'name': 'node1', 'status': 'READY'}, {'name': 'node2', 'status': 'READONLY'}]

        For all shards of the class:

        >>> client.schema.update_class_shard('Article', 'READONLY')
        [{'status': 'READONLY'},{'status': 'READONLY'}]
        >>> client.schema.get_class_shards('Article')
        [{'name': 'node1', 'status': 'READONLY'}, {'name': 'node2', 'status': 'READONLY'}]


        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        if not isinstance(class_name, str):
            raise TypeError(
                "'class_name' argument must be of type `str`! " f"Given type: {type(class_name)}."
            )
        if not isinstance(shard_name, str) and shard_name is not None:
            raise TypeError(
                "'shard_name' argument must be of type `str`! " f"Given type: {type(shard_name)}."
            )
        if not isinstance(status, str):
            raise TypeError(
                "'status' argument must be of type `str`! " f"Given type: {type(status)}."
            )

        if shard_name is None:
            shards_config = self.get_class_shards(
                class_name=class_name,
            )
            shard_names = [shard_config["name"] for shard_config in shards_config]
        else:
            shard_names = [shard_name]

        data = {"status": status}

        to_return = []

        for _shard_name in shard_names:
            path = f"/schema/{_capitalize_first_letter(class_name)}/shards/{_shard_name}"
            try:
                response = self._connection.put(
                    path=path,
                    weaviate_object=data,
                )
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError(
                    f"Class shards' status could not be updated for shard '{_shard_name}' due to "
                    "connection error."
                ) from conn_err

            to_return.append(
                _decode_json_response_dict(response, f"Update shard '{_shard_name}' status")
            )

        if shard_name is None:
            return to_return
        return cast(list, to_return[0])

    def _create_complex_properties_from_class(self, schema_class: dict) -> None:
        """
        Add cross-references to an already existing class.

        Parameters
        ----------
        schema_class : dict
            Description of the class that should be added.

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        if "properties" not in schema_class:
            # Class has no properties - nothing to do
            return
        for property_ in schema_class["properties"]:
            if _property_is_primitive(property_["dataType"]):
                continue

            # Create the property object. All complex dataTypes should be capitalized.
            schema_property = {
                "dataType": [_capitalize_first_letter(dtype) for dtype in property_["dataType"]],
                "name": property_["name"],
            }

            for property_field in PROPERTY_KEYS - {"name", "dataType"}:
                if property_field in property_:
                    schema_property[property_field] = property_[property_field]

            path = "/schema/" + _capitalize_first_letter(schema_class["class"]) + "/properties"
            try:
                response = self._connection.post(path=path, weaviate_object=schema_property)
            except RequestsConnectionError as conn_err:
                raise RequestsConnectionError(
                    "Property may not have been created properly."
                ) from conn_err
            if response.status_code != 200:
                raise UnexpectedStatusCodeException("Add properties to classes", response)

    def _create_complex_properties_from_classes(self, schema_classes_list: list) -> None:
        """
        Add cross-references to already existing classes.

        Parameters
        ----------
        schema_classes_list : list
            A list of classes as they are found in a schema JSON description.
        """

        for schema_class in schema_classes_list:
            self._create_complex_properties_from_class(schema_class)

    def _create_class_with_primitives(self, weaviate_class: dict) -> None:
        """
        Create class with only primitives.

        Parameters
        ----------
        weaviate_class : dict
            A single Weaviate formatted class

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        # Create the class
        schema_class = {
            "class": _capitalize_first_letter(weaviate_class["class"]),
            "properties": [],
        }

        for class_field in CLASS_KEYS - {"class", "properties"}:
            if class_field in weaviate_class:
                schema_class[class_field] = weaviate_class[class_field]

        if "properties" in weaviate_class:
            schema_class["properties"] = _get_primitive_properties(weaviate_class["properties"])

        # Add the item
        try:
            response = self._connection.post(path="/schema", weaviate_object=schema_class)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Class may not have been created properly.") from conn_err
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
            A list of classes as they are found in a schema JSON description.
        """

        for weaviate_class in schema_classes_list:
            self._create_class_with_primitives(weaviate_class)

    def add_class_tenants(self, class_name: str, tenants: List[Tenant]) -> None:
        """
        Add class's tenants in Weaviate.

        Parameters
        ----------
        class_name : str
            The class for which we add tenants.
        tenants : List[Tenant]
            List of Tenants.

        Examples
        --------
        >>> tenants = [ Tenant(name="Tenant1"), Tenant(name="Tenant2") ]
        >>> client.schema.add_class_tenants("class_name", tenants)

        Raises
        ------
        TypeError
            If 'tenants' has not the correct type.
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """

        loaded_tenants = [tenant._to_weaviate_object() for tenant in tenants]

        path = f"/schema/{_capitalize_first_letter(class_name)}/tenants"
        try:
            response = self._connection.post(path=path, weaviate_object=loaded_tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Classes tenants may not have been added properly."
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add classes tenants", response)

    def remove_class_tenants(self, class_name: str, tenants: List[str]) -> None:
        """
        Remove class's tenants in Weaviate.

        Parameters
        ----------
        class_name : str
            The class for which we remove tenants.
        tenants : List[str]
            List of tenant names to remove from the given class.

        Examples
        --------
        >>> client.schema.remove_class_tenants("class_name", ["Tenant1", "Tenant2"])

        Raises
        ------
        TypeError
            If 'tenants' has not the correct type.
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """
        path = f"/schema/{_capitalize_first_letter(class_name)}/tenants"
        try:
            response = self._connection.delete(path=path, weaviate_object=tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Classes tenants may not have been deleted."
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Delete classes tenants", response)

    def get_class_tenants(self, class_name: str) -> List[Tenant]:
        """Get class's tenants in Weaviate.

        Parameters
        ----------
        class_name : str
            The class for which we get tenants.

        Examples
        --------
        >>> client.schema.get_class_tenants("class_name")

        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """
        path = f"/schema/{_capitalize_first_letter(class_name)}/tenants"
        try:
            response = self._connection.get(path=path)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not get class tenants.") from conn_err

        tenant_resp = _decode_json_response_list(response, "Get class tenants")
        assert tenant_resp is not None
        return [Tenant._from_weaviate_object(tenant) for tenant in tenant_resp]

    def update_class_tenants(self, class_name: str, tenants: List[Tenant]) -> None:
        """Update class tenants.

        Use this when you want to move tenants from one activity state to another.

        Parameters
        ----------
        class_name : str
            The class for which we update tenants.
        tenants : List[Tenant]
            List of Tenants.

        Examples
        --------
        >>> client.schema.add_class_tenants(
                "class_name",
                [
                    Tenant(activity_status=TenantActivityStatus.HOT, name="Tenant1")),
                    Tenant(activity_status=TenantActivityStatus.COLD, name="Tenant2"))
                    Tenant(name="Tenant3")
                ]
            )
        >>> client.schema.update_class_tenants(
                "class_name",
                [
                    Tenant(activity_status=TenantActivityStatus.COLD, name="Tenant1")),
                    Tenant(activity_status=TenantActivityStatus.HOT, name="Tenant2"))
                ]
            )
        >>> client.schema.get_class_tenants("class_name")
        [
            Tenant(activity_status=TenantActivityStatus.COLD, name="Tenant1")),
            Tenant(activity_status=TenantActivityStatus.HOT, name="Tenant2")),
            Tenant(activity_status=TenantActivityStatus.HOT, name="Tenant3"))
        ]


        Raises
        ------
        requests.ConnectionError
            If the network connection to Weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If Weaviate reports a non-OK status.
        """
        path = f"/schema/{_capitalize_first_letter(class_name)}/tenants"
        loaded_tenants = [tenant._to_weaviate_object() for tenant in tenants]
        try:
            response = self._connection.put(path=path, weaviate_object=loaded_tenants)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Could not update class tenants.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Update classes tenants", response)


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
        A list of properties to extract the primitive properties.

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
    If a value of a key is a dict, it is going to be updated and not replaced by the whole dict.

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
            dict_1.update({key: value})
    return dict_1

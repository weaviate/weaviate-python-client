from typing import Dict, Any, List, Optional, Type, Tuple, cast

from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.collection.classes import (
    CollectionConfigUpdate,
    Model,
    PropertyType,
    _collection_config_from_json,
    _CollectionConfig,
    _Property,
)
from weaviate.connect import Connection
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    ObjectAlreadyExistsException,
    WeaviateAddInvalidPropertyError,
)


class _ConfigBase:
    """
    Represents all the CRUD methods available on a collection's configuration specification within Weaviate.

    This class should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.config` class attribute.
    """

    def __init__(self, connection: Connection, name: str) -> None:
        self.__connection = connection
        self._name = name

    def __get(self) -> Dict[str, Any]:
        try:
            response = self.__connection.get(path=f"/schema/{self._name}")
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Collection configuration could not be retrieved."
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Get collection configuration", response)
        return cast(Dict[str, Any], response.json())

    def get(self) -> _CollectionConfig:
        """Get the configuration for this collection from Weaviate.

        Raises:
        - `requests.ConnectionError`
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`
            - If Weaviate reports a non-OK status.
        """
        schema = self.__get()
        return _collection_config_from_json(schema)

    def update(self, config: CollectionConfigUpdate) -> None:
        """Update the configuration for this collection in Weaviate.

        Parameters:
        - config : The available options for updating a collection's configuration. If a property is not specified, it will
            not be updated.

        Raises:
        - `requests.ConnectionError`:
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`:
            - If Weaviate reports a non-OK status.

        NOTE:
        - If you wish to update a specific option within the configuration and cannot find it in `CollectionConfigUpdate` then
        it is an immutable option. To change it, you will have to delete the collection and recreate it with the
        desired options.
        - This is not the case of adding properties, which can be done with `collection.config.add_property()`.
        """
        schema = self.__get()
        schema = config.merge_with_existing(schema)
        try:
            response = self.__connection.put(path=f"/schema/{self._name}", weaviate_object=schema)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError(
                "Collection configuration could not be updated."
            ) from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Update collection configuration", response)

    def _add_property(self, additional_property: PropertyType) -> None:
        path = f"/schema/{self._name}/properties"
        obj = additional_property.to_dict()
        try:
            response = self.__connection.post(path=path, weaviate_object=obj)
        except RequestsConnectionError as conn_err:
            raise RequestsConnectionError("Property was not created properly.") from conn_err
        if response.status_code != 200:
            raise UnexpectedStatusCodeException("Add property to collection", response)

    def _get_property_by_name(self, property_name: str) -> Optional[_Property]:
        for prop in self.get().properties:
            if prop.name == property_name:
                return prop
        return None


class _ConfigCollection(_ConfigBase):
    def add_property(self, additional_property: PropertyType) -> None:
        """Add a property to the collection in Weaviate.

        Parameters:
        - additional_property : The property to add to the collection.

        Raises:
        - `requests.ConnectionError`:
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`:
            - If Weaviate reports a non-OK status.
        - `weaviate.ObjectAlreadyExistsException`:
            - If the property already exists in the collection.
        """
        if self._get_property_by_name(additional_property.name) is not None:
            raise ObjectAlreadyExistsException(
                f"Property with name '{additional_property.name}' already exists in collection '{self._name}'."
            )
        self._add_property(additional_property)


class _ConfigCollectionModel(_ConfigBase):
    def __compare_properties_with_model(
        self, schema_props: List[_Property], model_props: List[PropertyType]
    ) -> Tuple[List[_Property], List[PropertyType]]:
        only_in_model: List[PropertyType] = []
        only_in_schema: List[_Property] = list(schema_props)

        schema_props_simple = [
            {
                "name": prop.name,
                "dataType": prop.to_weaviate_dict().get("dataType"),
            }
            for prop in schema_props
        ]

        for prop in model_props:
            try:
                idx = schema_props_simple.index(
                    {"name": prop.name, "dataType": prop.to_dict().get("dataType")}
                )
                schema_props_simple.pop(idx)
                only_in_schema.pop(idx)
            except ValueError:
                only_in_model.append(prop)
        return only_in_schema, only_in_model

    def update_model(self, model: Type[Model]) -> None:
        only_in_schema, only_in_model = self.__compare_properties_with_model(
            self.get().properties, model.type_to_properties(model)
        )
        if len(only_in_schema) > 0:
            raise TypeError("Schema has extra properties")

        # we can only allow new optional types unless the default is None
        for prop in only_in_model:
            new_field = model.model_fields[prop.name]
            if new_field.annotation is None:
                continue  # if user did not annotate with type then ignore field
            non_optional_type = model.remove_optional_type(new_field.annotation)
            if new_field.default is not None and non_optional_type == new_field.annotation:
                raise WeaviateAddInvalidPropertyError(prop.name)

        for prop in only_in_model:
            self._add_property(prop)

    def is_invalid(self, model: Type[Model]) -> bool:
        only_in_schema, only_in_model = self.__compare_properties_with_model(
            self.get().properties, model.type_to_properties(model)
        )
        return len(only_in_schema) > 0 or len(only_in_model) > 0

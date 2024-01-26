from typing import Dict, List, Literal, Optional, Sequence, Type, Union, overload

from weaviate.collections.base import _CollectionsBase
from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    _CollectionConfigCreate,
    _GenerativeConfigCreate,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    _VectorIndexConfigCreate,
    Property,
    _ShardingConfigCreate,
    _ReferencePropertyBase,
    _ReplicationConfigCreate,
    _RerankerConfigCreate,
    _VectorizerConfigCreate,
    _Vectorizer,
)
from weaviate.collections.classes.internal import References, _check_references_generic
from weaviate.collections.classes.types import Properties, _check_properties_generic
from weaviate.collections.collection import Collection
from weaviate.collections.validator import _raise_invalid_input
from weaviate.util import _capitalize_first_letter


class _Collections(_CollectionsBase):
    def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        generative_config: Optional[_GenerativeConfigCreate] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[Sequence[Union[Property, _ReferencePropertyBase]]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        reranker_config: Optional[_RerankerConfigCreate] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorizer_config: Optional[_VectorizerConfigCreate] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
    ) -> Collection[Properties, References]:
        """Use this method to create a collection in Weaviate and immediately return a collection object.

        This method takes several arguments that allow you to configure the collection to your liking. Each argument
        can be produced by using the `Configure` class in `weaviate.classes` to generate the specific configuration
        object that you require given your use case.

        Inspect [the docs](https://weaviate.io/developers/weaviate/configuration) for more information on the different
        configuration options and how they affect the behavior of your collection.

        This method sends a request to Weaviate to create the collection given the configuration. It then returns the newly
        created collection Python object for you to use to make requests.

        Arguments:
            `name`
                The name of the collection to create.
            `description`
                A description of the collection to create.
            `generative_config`
                The configuration for Weaviate's generative capabilities.
            `inverted_index_config`
                The configuration for Weaviate's inverted index.
            `multi_tenancy_config`
                The configuration for Weaviate's multi-tenancy capabilities.
            `properties`
                The properties of the objects in the collection.
            `references`
                The references of the objects in the collection.
            `replication_config`
                The configuration for Weaviate's replication strategy.
            `sharding_config`
                The configuration for Weaviate's sharding strategy.
            `vector_index_config`
                The configuration for Weaviate's vector index.
            `vectorizer_config`
                The configuration for Weaviate's vectorizer.
            `data_model_properties`
                The generic class that you want to use to represent the properties of objects in this collection. See the `get` method for more information.
            `data_model_references`
                The generic class that you want to use to represent the references of objects in this collection. See the `get` method for more information.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `pydantic.ValidationError`
                If the configuration object is invalid.
        """
        config = _CollectionConfigCreate(
            description=description,
            generative_config=generative_config,
            inverted_index_config=inverted_index_config,
            multi_tenancy_config=multi_tenancy_config,
            name=name,
            properties=properties,
            references=references,
            replication_config=replication_config,
            reranker_config=reranker_config,
            sharding_config=sharding_config,
            vectorizer_config=vectorizer_config or _Vectorizer.none(),
            vector_index_config=vector_index_config,
        )
        name = super()._create(config._to_dict())
        if config.name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config.name})"
            )
        return self.get(name, data_model_properties, data_model_references)

    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
    ) -> Collection[Properties, References]:
        """Use this method to return a collection object to be used when interacting with your Weaviate collection.

        This method does not send a request to Weaviate. It simply creates a Python object for you to use to make requests.

        Arguments:
            `name`
                The name of the collection to get.
            `data_model_properties`
                The generic class that you want to use to represent the properties of objects in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return objects properties as `Dict[str, Any]`.
            `data_model_references`
                The generic class that you want to use to represent the objects of references in this collection when mutating objects through the `.query` namespace.
                The generic provided in this argument will propagate to the methods in `.query` and allow you to do `mypy` static type checking on your codebase.
                If you do not provide a generic, the methods in `.query` will return properties of referenced objects as `Dict[str, Any]`.

        Raises:
            `weaviate.exceptions.InvalidDataModelException`
                If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        if not isinstance(name, str):
            _raise_invalid_input("name", name, str)
        _check_properties_generic(data_model_properties)
        _check_references_generic(data_model_references)
        name = _capitalize_first_letter(name)
        return Collection[Properties, References](
            self._connection,
            name,
            properties=data_model_properties,
            references=data_model_references,
        )

    def delete(self, name: Union[str, List[str]]) -> None:
        """Use this method to delete collection(s) from the Weaviate instance by its/their name(s).

        WARNING: If you have instances of client.collections.get() or client.collections.create()
        for these collections within your code, they will cease to function correctly after this operation.

        Arguments:
            `name`
                The name(s) of the collection(s) to delete.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        if not isinstance(name, str) and (
            not isinstance(name, list) or not all(isinstance(n, str) for n in name)
        ):
            _raise_invalid_input("name", name, Union[str, List[str]])

        if isinstance(name, str):
            self._delete(_capitalize_first_letter(name))
        else:
            for n in name:
                self._delete(_capitalize_first_letter(n))

    def delete_all(self) -> None:
        """Use this method to delete all collections from the Weaviate instance.

        WARNING: If you have instances of client.collections.get() or client.collections.create()
        for these collections within your code, they will cease to function correctly after this operation.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        for name in self.list_all().keys():
            self.delete(name)

    def exists(self, name: str) -> bool:
        """Use this method to check if a collection exists in the Weaviate instance.

        Arguments:
            `name`
                The name of the collection to check.

        Returns:
            `True` if the collection exists, `False` otherwise.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        if not isinstance(name, str):
            _raise_invalid_input("name", name, str)
        return self._exists(_capitalize_first_letter(name))

    def export_config(self, name: str) -> CollectionConfig:
        """Use this method to export the configuration of a collection from the Weaviate instance.

        Arguments:
            `name`
                The name of the collection to export.

        Returns:
            The configuration of the collection as a `CollectionConfig` object.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return self._export(_capitalize_first_letter(name))

    @overload
    def list_all(self, simple: Literal[False]) -> Dict[str, CollectionConfig]:
        ...

    @overload
    def list_all(self, simple: Literal[True] = ...) -> Dict[str, CollectionConfigSimple]:
        ...

    @overload
    def list_all(
        self, simple: bool = ...
    ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]:
        ...

    def list_all(
        self, simple: bool = True
    ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]:
        """List the configurations of the all the collections currently in the Weaviate instance.

        Arguments:
            `simple`
                If `True`, return a simplified version of the configuration containing only name and properties.

        Returns:
            A dictionary containing the configurations of all the collections currently in the Weaviate instance mapping
            collection name to collection configuration.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        if not isinstance(simple, bool):
            _raise_invalid_input("simple", simple, bool)
        if simple:
            return self._get_simple()
        return self._get_all()

    def create_from_dict(self, config: dict) -> Collection:
        """Use this method to create a collection in Weaviate and immediately return a collection object using a pre-defined Weaviate collection configuration dictionary object.

        This method is helpful for those making the v3 -> v4 migration and for those interfacing with any experimental
        Weaviate features that are not yet fully supported by the Weaviate Python client.

        Arguments:
            `config`
                The dictionary representation of the collection's configuration.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        if "name" in config:
            config["class"] = config.pop("name")
        name = super()._create(config)
        return self.get(name)

    def create_from_config(self, config: CollectionConfig) -> Collection:
        """Use this method to create a collection in Weaviate and immediately return a collection object using a pre-defined Weaviate collection configuration object.

        Arguments:
            `config`
                The collection's configuration.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return self.create_from_dict(config.to_dict())

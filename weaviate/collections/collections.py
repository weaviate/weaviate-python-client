from typing import Dict, List, Literal, Optional, Type, Union, overload

from weaviate.collections.base import _CollectionsBase
from weaviate.collections.classes.config import (
    _CollectionConfig,
    _CollectionConfigSimple,
    _CollectionConfigCreate,
    _GenerativeConfig,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    Property,
    _ShardingConfigCreate,
    _ReferencePropertyBase,
    _ReplicationConfigCreate,
    _VectorizerConfig,
    _Vectorizer,
    _VectorIndexConfigCreate,
    _VectorIndexType,
)
from weaviate.collections.classes.types import Properties, _check_data_model
from weaviate.collections.collection import Collection
from weaviate.util import _capitalize_first_letter


class _Collections(_CollectionsBase):
    def create(
        self,
        name: str,
        description: Optional[str] = None,
        generative_config: Optional[_GenerativeConfig] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[List[Union[Property, _ReferencePropertyBase]]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vector_index_type: _VectorIndexType = _VectorIndexType.HNSW,
        vectorizer_config: Optional[_VectorizerConfig] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> Collection[Properties]:
        """Use this method to create a collection in Weaviate and immediately return a collection object.

        This method takes several arguments that allow you to configure the collection to your liking. Each argument
        can be produced by using the `Configure` class in `weaviate.classes` to generate the specific configuration
        object that you require given your use case.

        Inspect [the docs](https://weaviate.io/developers/weaviate/configuration) for more information on the different
        configuration options and how they affect the behavior of your collection.

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
            `replication_config`
                The configuration for Weaviate's replication strategy.
            `sharding_config`
                The configuration for Weaviate's sharding strategy.
            `vector_index_config`
                The configuration for Weaviate's vector index.
            `vector_index_type`
                The type of vector index to use.
            `vectorizer_config`
                The configuration for Weaviate's vectorizer.
            `data_model`
                The generic class that you want to use to represent the properties of objects in this collection. See the `get` method for more information.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
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
            replication_config=replication_config,
            sharding_config=sharding_config,
            vectorizer_config=vectorizer_config or _Vectorizer.none(),
            vector_index_config=vector_index_config,
            vector_index_type=vector_index_type,
        )
        name = super()._create(config)
        if config.name != name:
            raise ValueError(
                f"Name of created collection ({name}) does not match given name ({config.name})"
            )
        return self.get(name, data_model)

    def get(
        self, name: str, data_model: Optional[Type[Properties]] = None
    ) -> Collection[Properties]:
        """Use this method to return a collection object to be used when interacting with your Weaviate collection.

        Arguments:
            `name`
                The name of the collection to get.
            `data_model`
                The generic class that you want to use to represent the properties of objects in this collection when mutating objects through the `.data` namespace.
                    The generic provided in this argument will propagate to the methods in `.data` and allow you to do `mypy` static type checking on your codebase.
                        If you do not provide a generic, the methods in `.data` will return objects of `Dict[str, Any]` type.

        Raises:
            `weaviate.exceptions.InvalidDataModelException`
                If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        _check_data_model(data_model)
        name = _capitalize_first_letter(name)
        return Collection[Properties](self._connection, name, type_=data_model)

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
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
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
            `weaviate.UnexpectedStatusCodeException`
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
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        return self._exists(_capitalize_first_letter(name))

    @overload
    def list_all(self, simple: Literal[False]) -> Dict[str, _CollectionConfig]:
        ...

    @overload
    def list_all(self, simple: Literal[True] = ...) -> Dict[str, _CollectionConfigSimple]:
        ...

    def list_all(
        self, simple: bool = True
    ) -> Union[Dict[str, _CollectionConfig], Dict[str, _CollectionConfigSimple]]:
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
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        if simple:
            return self._get_simple()
        return self._get_all()

from abc import abstractmethod
from typing import (
    Awaitable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    Union,
)

from weaviate.collections.classes.config import (
    _NamedVectorConfigCreate,
    CollectionConfig,
    CollectionConfigSimple,
    _GenerativeProvider,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    _VectorIndexConfigCreate,
    Property,
    _ShardingConfigCreate,
    _ReferencePropertyBase,
    _ReplicationConfigCreate,
    _RerankerProvider,
    _VectorizerConfigCreate,
)
from weaviate.collections.classes.internal import References
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.collection import CollectionAsync, Collection
from weaviate.collections.collections.executor import _CollectionsExecutor
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType


class _CollectionsBase(Generic[ConnectionType]):
    _executor = _CollectionsExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection

    @abstractmethod
    def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[Sequence[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        reranker_config: Optional[_RerankerProvider] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Union[
        Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
    ]:
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
                The configuration for Weaviate's default vector index.
            `vectorizer_config`
                The configuration for Weaviate's default vectorizer or a list of named vectorizers.
            `data_model_properties`
                The generic class that you want to use to represent the properties of objects in this collection. See the `get` method for more information.
            `data_model_references`
                The generic class that you want to use to represent the references of objects in this collection. See the `get` method for more information.
            `skip_argument_validation`
                If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.

        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.exceptions.WeaviateUnsupportedFeatureError`
                If the Weaviate version is lower than 1.24.0 and named vectorizers are provided.
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Union[Collection[Properties, References], CollectionAsync[Properties, References]]:
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
            `skip_argument_validation`
                If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.
        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.exceptions.InvalidDataModelException`
                If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        raise NotImplementedError()

    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> Union[Collection[Properties, References], CollectionAsync[Properties, References]]:
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
            `skip_argument_validation`
                If arguments to functions such as near_vector should be validated. Disable this if you need to squeeze out some extra performance.
        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.exceptions.InvalidDataModelException`
                If the data model is not a valid data model, i.e., it is not a `dict` nor a `TypedDict`.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, name: Union[str, List[str]]) -> ExecutorResult[None]:
        """Use this method to delete collection(s) from the Weaviate instance by its/their name(s).

        WARNING: If you have instances of `client.collections.use()` or `client.collections.create()`
        for these collections within your code, they will cease to function correctly after this operation.

        Arguments:
            `name`
                The name(s) of the collection(s) to delete.

        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete_all(self) -> ExecutorResult[None]:
        """Use this method to delete all collections from the Weaviate instance.

        WARNING: If you have instances of `client.collections.use()` or client.collections.create()
        for these collections within your code, they will cease to function correctly after this operation.

        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def exists(self, name: str) -> ExecutorResult[bool]:
        """Use this method to check if a collection exists in the Weaviate instance.

        Arguments:
            `name`
                The name of the collection to check.

        Returns:
            `True` if the collection exists, `False` otherwise.

        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def export_config(self, name: str) -> ExecutorResult[CollectionConfig]:
        """Use this method to export the configuration of a collection from the Weaviate instance.

        Arguments:
            `name`
                The name of the collection to export.

        Returns:
            The configuration of the collection as a `CollectionConfig` object.

        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def list_all(
        self, simple: bool = True
    ) -> ExecutorResult[Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]]:
        """List the configurations of the all the collections currently in the Weaviate instance.

        Arguments:
            `simple`
                If `True`, return a simplified version of the configuration containing only name and properties.

        Returns:
            A dictionary containing the configurations of all the collections currently in the Weaviate instance mapping
            collection name to collection configuration.

        Raises:
            `weaviate.WeaviateInvalidInputError`
                If the input parameters are invalid.
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    def create_from_dict(
        self, config: dict
    ) -> Union[
        Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
    ]:
        """Use this method to create a collection in Weaviate and immediately return a collection object using a pre-defined Weaviate collection configuration dictionary object.

        This method is helpful for those making the v3 -> v4 migration and for those interfacing with any experimental
        Weaviate features that are not yet fully supported by the Weaviate Python client.

        Arguments:
            `config`
                The dictionary representation of the collection's configuration.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    def create_from_config(
        self, config: CollectionConfig
    ) -> Union[
        Collection[Properties, References], Awaitable[CollectionAsync[Properties, References]]
    ]:
        """Use this method to create a collection in Weaviate and immediately return a collection object using a pre-defined Weaviate collection configuration object.

        Arguments:
            `config`
                The collection's configuration.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

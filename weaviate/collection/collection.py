from typing import Dict, Generic, List, Literal, Optional, Type, Union, cast, overload
from typing_extensions import is_typeddict

from weaviate.collection.classes.config import (
    _CollectionConfigCreate,
    _CollectionConfig,
    _CollectionConfigSimple,
    ConsistencyLevel,
    _GenerativeConfig,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    Property,
    _ShardingConfigCreate,
    _ReferencePropertyBase,
    _ReplicationConfigCreate,
    _VectorizerConfig,
    _VectorizerFactory,
    _VectorIndexConfigCreate,
    _VectorIndexType,
)
from weaviate.collection.classes.grpc import MetadataQuery, PROPERTIES
from weaviate.collection.classes.types import Properties, TProperties, _check_data_model
from weaviate.collection.collection_base import _CollectionBase, _CollectionObjectBase
from weaviate.collection.config import _ConfigCollection
from weaviate.collection.data import _DataCollection
from weaviate.collection.grpc import _GenerateCollection, _GroupByCollection, _QueryCollection
from weaviate.collection.object_iterator import _ObjectIterator
from weaviate.collection.tenants import _Tenants
from weaviate.connect import Connection
from weaviate.util import _capitalize_first_letter


class _CollectionObject(_CollectionObjectBase, Generic[Properties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        type_: Optional[Type[Properties]] = None,
    ) -> None:
        super().__init__(name)

        self._connection = connection

        self.config = _ConfigCollection(self._connection, name)
        """This namespace includes all the CRUD methods available to you when modifying the configuration of the collection in Weaviate."""
        self.data = _DataCollection[Properties](connection, name, consistency_level, tenant, type_)
        """This namespace includes all the CUD methods available to you when modifying the data of the collection in Weaviate."""
        self.generate = _GenerateCollection(connection, name, consistency_level, tenant, type_)
        """This namespace includes all the querying methods available to you when using Weaviate's generative capabilities."""
        self.query_group_by = _GroupByCollection(connection, name, consistency_level, tenant, type_)
        """This namespace includes all the querying methods available to you when using Weaviate's group-by capabilities."""
        self.query = _QueryCollection[Properties](
            connection, name, self.data, consistency_level, tenant, type_
        )
        """This namespace includes all the querying methods available to you when using Weaviate's standard query capabilities."""
        self.tenants = _Tenants(connection, name)
        """This namespace includes all the CRUD methods available to you when modifying the tenants of a multi-tenancy-enabled collection in Weaviate."""

        self.__tenant = tenant
        self.__consistency_level = consistency_level
        self.__type = type_

    def with_tenant(self, tenant: Optional[str] = None) -> "_CollectionObject":
        """Use this method to return a collection object specific to a single tenant.

        If multi-tenancy is not configured for this collection then Weaviate will throw an error.

        Arguments:
            `tenant`
                The name of the tenant to use.
        """
        return _CollectionObject(self._connection, self.name, self.__consistency_level, tenant)

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "_CollectionObject":
        """Use this method to return a collection object specific to a single consistency level.

        If replication is not configured for this collection then Weaviate will throw an error.

        Arguments:
            `consistency_level`
                The consistency level to use.
        """
        return _CollectionObject(self._connection, self.name, consistency_level, self.__tenant)

    @overload
    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> _ObjectIterator[Properties]:
        ...

    @overload
    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        *,
        return_properties: Type[TProperties],
    ) -> _ObjectIterator[TProperties]:
        ...

    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[TProperties]]] = None,
    ) -> Union[_ObjectIterator[Properties], _ObjectIterator[TProperties]]:
        """Use this method to return an iterator over the objects in the collection.

        This iterator keeps a record of the last object that it returned to be used in each subsequent call to
        Weaviate. Once the collection is exhausted, the iterator exits.

        If `return_metadata` and `return_properties` are not provided, all the data of each object will be
        requested from Weaviate except for its vector as this is an expensive operation. Specify `return_metadata`
        and `return_properties` to only request the data that you need.

        Arguments:
            `return_metadata`
                The metadata to return with each object.
            `return_properties`
                The properties to return with each object.

        Raises:
            `requests.ConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If Weaviate reports a non-OK status.
        """
        if is_typeddict(return_properties):
            return_properties = cast(Type[TProperties], return_properties)
            return _ObjectIterator[TProperties](
                lambda limit, alpha, meta: self.query.fetch_objects(
                    limit=limit,
                    after=alpha,
                    return_metadata=meta,
                    return_properties=return_properties,
                ).objects,
                return_metadata,
                return_properties,
            )
        if return_properties is None and self.__type is not None:
            _type = cast(Type[Properties], self.__type)
            return _ObjectIterator[Properties](
                lambda limit, alpha, meta: self.query.fetch_objects(
                    limit=limit,
                    after=alpha,
                    return_metadata=meta,
                    return_properties=_type,
                ).objects,
                return_metadata,
                _type,
            )
        props = cast(PROPERTIES, return_properties)
        return _ObjectIterator[Properties](
            lambda limit, alpha, meta: self.query.fetch_objects(
                limit=limit,
                after=alpha,
                return_metadata=meta,
                return_properties=props,
            ).objects,
            return_metadata,
            props,
        )


class _Collection(_CollectionBase):
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
    ) -> _CollectionObject[Properties]:
        """Use this method to create a collection in Weaviate and immediately return a collection object.

        This method takes several arguments that allow you to configure the collection to your liking. Each argument
        can be produced by using the `ConfigFactory` class in `weaviate.classes` to generate the specific configuration
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
            vectorizer_config=vectorizer_config or _VectorizerFactory.none(),
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
    ) -> _CollectionObject[Properties]:
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
        return _CollectionObject[Properties](self._connection, name, type_=data_model)

    def delete(self, name: Union[str, List[str]]) -> None:
        """Use this method to delete collection(s) from the Weaviate instance by its/their name(s).

        WARNING: If you have instances of client.collection.get() or client.collection.create()
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

    def exists(self, name: str) -> bool:
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

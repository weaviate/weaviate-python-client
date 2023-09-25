from typing import Dict, Generic, List, Literal, Optional, Type, Union, overload

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
    ReferencePropertyBase,
    _ReplicationConfigCreate,
    _VectorizerConfig,
    _VectorizerFactory,
    _VectorIndexConfigCreate,
    VectorIndexType,
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


class _CollectionObject(_CollectionObjectBase, Generic[TProperties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        type_: Optional[Type[TProperties]] = None,
    ) -> None:
        super().__init__(name)

        self._connection = connection

        self.config = _ConfigCollection(self._connection, name)
        self.data = _DataCollection[TProperties](connection, name, consistency_level, tenant, type_)
        self.generate = _GenerateCollection(connection, name, consistency_level, tenant)
        self.query_group_by = _GroupByCollection(connection, name, consistency_level, tenant)
        self.query = _QueryCollection[TProperties](
            connection, name, self.data, consistency_level, tenant
        )
        self.tenants = _Tenants(connection, name)

        self.__tenant = tenant
        self.__consistency_level = consistency_level

    def with_tenant(self, tenant: Optional[str] = None) -> "_CollectionObject":
        return _CollectionObject(self._connection, self.name, self.__consistency_level, tenant)

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "_CollectionObject":
        return _CollectionObject(self._connection, self.name, consistency_level, self.__tenant)

    def iterator(
        self,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _ObjectIterator[Properties, TProperties]:
        return _ObjectIterator[Properties, TProperties](
            self.query, return_metadata, return_properties
        )


class _Collection(_CollectionBase):
    def create(
        self,
        name: str,
        description: Optional[str] = None,
        generative_config: Optional[_GenerativeConfig] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[List[Union[Property, ReferencePropertyBase]]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vector_index_type: VectorIndexType = VectorIndexType.HNSW,
        vectorizer_config: Optional[_VectorizerConfig] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> _CollectionObject[Properties]:
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
        _check_data_model(data_model)
        name = _capitalize_first_letter(name)
        return _CollectionObject[Properties](self._connection, name, type_=data_model)

    def delete(self, name: Union[str, List[str]]) -> None:
        """Use this method to delete collection(s) from the Weaviate instance by its/their name(s).

        WARNING: If you have instances of client.collection.get() or client.collection.create()
        for these collections within your code, they will cease to function correctly after this operation.

        Arguments:
        - name: The names of the collections to delete.

        Raises:
        - `requests.ConnectionError`
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`
            - If Weaviate reports a non-OK status.
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
        - simple : If True, return a simplified version of the configuration containing only name and properties.

        Raises:
        - `requests.ConnectionError`
            - If the network connection to Weaviate fails.
        - `weaviate.UnexpectedStatusCodeException`
            - If Weaviate reports a non-OK status.
        """
        if simple:
            return self._get_simple()
        return self._get_all()

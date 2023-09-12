from typing import Generic, List, Optional, Type, Union

from weaviate.collection.classes.config import (
    CollectionConfigCreate,
    ConsistencyLevel,
    GenerativeConfig,
    InvertedIndexConfigCreate,
    MultiTenancyConfig,
    Property,
    ShardingConfigCreate,
    ReferencePropertyBase,
    ReplicationConfigCreate,
    VectorizerConfig,
    VectorizerFactory,
    VectorIndexConfigCreate,
    VectorIndexType,
)
from weaviate.collection.classes.types import Properties, _check_data_model
from weaviate.collection.collection_base import CollectionBase
from weaviate.collection.config import _ConfigCollection
from weaviate.collection.data import _DataCollection
from weaviate.collection.grpc import _GrpcCollection
from weaviate.collection.tenants import _Tenants
from weaviate.connect import Connection
from weaviate.util import _capitalize_first_letter


class CollectionObject(Generic[Properties]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        tenant: Optional[str] = None,
        type_: Optional[Type[Properties]] = None,
    ) -> None:
        self._connection = connection
        self.name = name

        self.config = _ConfigCollection(self._connection, name)
        self.data = _DataCollection[Properties](connection, name, consistency_level, tenant, type_)
        self.query = _GrpcCollection(connection, name, consistency_level, tenant)
        self.tenants = _Tenants(connection, name)

        self.__tenant = tenant
        self.__consistency_level = consistency_level

    def with_tenant(self, tenant: Optional[str] = None) -> "CollectionObject":
        return CollectionObject(self._connection, self.name, self.__consistency_level, tenant)

    def with_consistency_level(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> "CollectionObject":
        return CollectionObject(self._connection, self.name, consistency_level, self.__tenant)


class Collection(CollectionBase):
    def create(
        self,
        name: str,
        data_model: Optional[Type[Properties]] = None,
        description: Optional[str] = None,
        generative_search: Optional[GenerativeConfig] = None,
        inverted_index_config: Optional[InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[MultiTenancyConfig] = None,
        properties: Optional[List[Union[Property, ReferencePropertyBase]]] = None,
        replication_config: Optional[ReplicationConfigCreate] = None,
        sharding_config: Optional[ShardingConfigCreate] = None,
        vector_index_config: Optional[VectorIndexConfigCreate] = None,
        vector_index_type: VectorIndexType = VectorIndexType.HNSW,
        vectorizer_config: Optional[VectorizerConfig] = None,
    ) -> CollectionObject[Properties]:
        config = CollectionConfigCreate(
            description=description,
            generative_search=generative_search,
            inverted_index_config=inverted_index_config,
            multi_tenancy_config=multi_tenancy_config,
            name=name,
            properties=properties,
            replication_config=replication_config,
            sharding_config=sharding_config,
            vectorizer_config=vectorizer_config or VectorizerFactory.none(),
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
    ) -> CollectionObject[Properties]:
        _check_data_model(data_model)
        name = _capitalize_first_letter(name)
        return CollectionObject[Properties](self._connection, name, type_=data_model)

    def delete(self, name: str) -> None:
        """Use this method to delete a collection from the Weaviate instance by its name.

        WARNING: If you have instances of client.collection.get() or client.collection.create()
        for this collection within your code, they will cease to function correctly after this operation.

        Parameters:
        - name: The name of the collection to delete.
        """
        self._delete(_capitalize_first_letter(name))

    def exists(self, name: str) -> bool:
        return self._exists(_capitalize_first_letter(name))

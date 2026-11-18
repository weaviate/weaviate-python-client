from typing import Dict, List, Literal, Optional, Sequence, Type, Union, overload

from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    GenerativeProvider,
    InvertedIndexConfigCreate,
    MultiTenancyConfigCreate,
    Property,
    ReferencePropertyBase,
    ReplicationConfigCreate,
    RerankerProvider,
    ShardingConfigCreate,
)
from weaviate.collections.classes.config_named_vectors import _NamedVectorConfigCreate
from weaviate.collections.classes.config_object_ttl import ObjectTTLConfigCreate
from weaviate.collections.classes.config_vector_index import VectorIndexConfigCreate
from weaviate.collections.classes.config_vectorizers import _VectorizerConfigCreate
from weaviate.collections.classes.config_vectors import VectorConfigCreate
from weaviate.collections.classes.internal import References
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.collection import CollectionAsync
from weaviate.collections.collections.base import _CollectionsBase
from weaviate.connect.v4 import ConnectionAsync

class _CollectionsAsync(_CollectionsBase[ConnectionAsync]):
    @overload
    async def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        generative_config: Optional[GenerativeProvider] = None,
        inverted_index_config: Optional[InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[MultiTenancyConfigCreate] = None,
        object_ttl_config: Optional[ObjectTTLConfigCreate] = None,
        properties: Optional[Sequence[Property]] = None,
        references: Optional[List[ReferencePropertyBase]] = None,
        replication_config: Optional[ReplicationConfigCreate] = None,
        reranker_config: Optional[RerankerProvider] = None,
        sharding_config: Optional[ShardingConfigCreate] = None,
        vector_index_config: Optional[VectorIndexConfigCreate] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        vector_config: Optional[Union[VectorConfigCreate, List[VectorConfigCreate]]] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    @overload
    @deprecated(
        'Using the "vectorizer_config" argument is deprecated. Instead, use the "vector_config" argument.'
    )
    async def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        generative_config: Optional[GenerativeProvider] = None,
        inverted_index_config: Optional[InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[MultiTenancyConfigCreate] = None,
        object_ttl_config: Optional[ObjectTTLConfigCreate] = None,
        properties: Optional[Sequence[Property]] = None,
        references: Optional[List[ReferencePropertyBase]] = None,
        replication_config: Optional[ReplicationConfigCreate] = None,
        reranker_config: Optional[RerankerProvider] = None,
        sharding_config: Optional[ShardingConfigCreate] = None,
        vector_index_config: VectorIndexConfigCreate,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        vector_config: Optional[Union[VectorConfigCreate, List[VectorConfigCreate]]] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    @overload
    @deprecated(
        'Using the "vectorizer_config" argument is deprecated. Instead, use the "vector_config" argument.'
    )
    async def create(
        self,
        name: str,
        *,
        description: Optional[str] = None,
        generative_config: Optional[GenerativeProvider] = None,
        inverted_index_config: Optional[InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[MultiTenancyConfigCreate] = None,
        object_ttl_config: Optional[ObjectTTLConfigCreate] = None,
        properties: Optional[Sequence[Property]] = None,
        references: Optional[List[ReferencePropertyBase]] = None,
        replication_config: Optional[ReplicationConfigCreate] = None,
        reranker_config: Optional[RerankerProvider] = None,
        sharding_config: Optional[ShardingConfigCreate] = None,
        vector_index_config: Optional[VectorIndexConfigCreate] = None,
        vectorizer_config: Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]],
        vector_config: Optional[Union[VectorConfigCreate, List[VectorConfigCreate]]] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    def get(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    def use(
        self,
        name: str,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    async def delete(self, name: Union[str, List[str]]) -> None: ...
    async def delete_all(self) -> None: ...
    async def exists(self, name: str) -> bool: ...
    async def export_config(self, name: str) -> CollectionConfig: ...
    @overload
    async def list_all(self, simple: Literal[False]) -> Dict[str, CollectionConfig]: ...
    @overload
    async def list_all(self, simple: Literal[True] = ...) -> Dict[str, CollectionConfigSimple]: ...
    @overload
    async def list_all(
        self, simple: bool = ...
    ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]: ...
    async def list_all(
        self, simple: bool = True
    ) -> Union[Dict[str, CollectionConfig], Dict[str, CollectionConfigSimple]]: ...
    async def create_from_dict(self, config: dict) -> CollectionAsync: ...
    async def create_from_config(self, config: CollectionConfig) -> CollectionAsync: ...

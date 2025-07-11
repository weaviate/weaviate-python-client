from typing import Dict, List, Literal, Optional, Sequence, Type, Union, overload

from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    Property,
    _GenerativeProvider,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    _NamedVectorConfigCreate,
    _ReferencePropertyBase,
    _ReplicationConfigCreate,
    _RerankerProvider,
    _ShardingConfigCreate,
    _VectorConfigCreate,
    _VectorIndexConfigCreate,
    _VectorizerConfigCreate,
)
from weaviate.collections.classes.internal import References
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.collection import CollectionAsync
from weaviate.collections.collections.base import _CollectionsBase
from weaviate.connect.v4 import ConnectionAsync

class _CollectionsAsync(_CollectionsBase[ConnectionAsync]):
    @overload
    @deprecated(
        'Using the "vector_index_config" argument is deprecated. Instead, define the vector index for each specific vectorizer supplied to the "vectorizers_config" argument.'
    )
    async def create(
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
        vector_index_config: _VectorIndexConfigCreate,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        vector_config: Optional[Union[_VectorConfigCreate, List[_VectorConfigCreate]]] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    @overload
    @deprecated(
        'Using the "vectorizer_config" argument is deprecated. Instead, use the "vectorizers_config" argument.'
    )
    async def create(
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
        vectorizer_config: Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]],
        vector_config: Optional[Union[_VectorConfigCreate, List[_VectorConfigCreate]]] = None,
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_references: Optional[Type[References]] = None,
        skip_argument_validation: bool = False,
    ) -> CollectionAsync[Properties, References]: ...
    @overload
    async def create(
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
        vector_config: Optional[Union[_VectorConfigCreate, List[_VectorConfigCreate]]] = None,
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

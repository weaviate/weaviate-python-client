from typing import Dict, List, Literal, Optional, Union, overload

from weaviate.collections.classes.config import (
    _InvertedIndexConfigUpdate,
    _ReplicationConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    Property,
    ReferenceProperty,
    _ReferencePropertyMultiTarget,
    _VectorIndexConfigHNSWUpdate,
    CollectionConfig,
    CollectionConfigSimple,
    ShardStatus,
    ShardTypes,
    _NamedVectorConfigUpdate,
    _MultiTenancyConfigUpdate,
    _GenerativeProvider,
    _RerankerProvider,
)
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate
from weaviate.collections.config.base import _ConfigCollectionBase
from weaviate.connect.v4 import ConnectionAsync

class _ConfigCollectionAsync(_ConfigCollectionBase[ConnectionAsync]):
    @overload
    async def get(self, simple: Literal[False] = ...) -> CollectionConfig: ...
    @overload
    async def get(self, simple: Literal[True]) -> CollectionConfigSimple: ...
    @overload
    async def get(self, simple: bool = ...) -> Union[CollectionConfig, CollectionConfigSimple]: ...
    async def update(
        self,
        *,
        description: Optional[str] = None,
        property_descriptions: Optional[Dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigUpdate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
            ]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> None: ...
    async def get_shards(self) -> List[ShardStatus]: ...
    async def update_shards(
        self,
        status: Literal["READY", "READONLY"],
        shard_names: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, ShardTypes]: ...
    async def add_property(self, prop: Property) -> None: ...
    async def add_reference(
        self, ref: Union[ReferenceProperty, _ReferencePropertyMultiTarget]
    ) -> None: ...

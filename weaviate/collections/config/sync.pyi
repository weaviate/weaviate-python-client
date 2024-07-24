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
)

from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate

from weaviate.collections.config.config import _ConfigCollectionBase

class _ConfigCollection(_ConfigCollectionBase):
    @overload
    def get(self, simple: Literal[False] = ...) -> CollectionConfig: ...
    @overload
    def get(self, simple: Literal[True]) -> CollectionConfigSimple: ...
    @overload
    def get(self, simple: bool = ...) -> Union[CollectionConfig, CollectionConfigSimple]: ...
    def update(
        self,
        *,
        description: Optional[str] = None,
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
    ) -> None: ...
    def get_shards(self) -> List[ShardStatus]: ...
    def update_shards(
        self,
        status: Literal["READY", "READONLY"],
        shard_names: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, ShardTypes]: ...
    def add_property(self, prop: Property) -> None: ...
    def add_reference(
        self, ref: Union[ReferenceProperty, _ReferencePropertyMultiTarget]
    ) -> None: ...

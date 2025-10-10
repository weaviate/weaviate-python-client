from typing import Literal, Optional, overload

from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    Property,
    ReferenceProperty,
    ShardStatus,
    ShardTypes,
    _GenerativeProvider,
    _InvertedIndexConfigUpdate,
    _MultiTenancyConfigUpdate,
    _NamedVectorConfigCreate,
    _NamedVectorConfigUpdate,
    _ReferencePropertyMultiTarget,
    _ReplicationConfigUpdate,
    _RerankerProvider,
    _VectorConfigCreate,
    _VectorConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    _VectorIndexConfigHNSWUpdate,
)
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate
from weaviate.connect.v4 import ConnectionSync

from .executor import _ConfigCollectionExecutor

class _ConfigCollection(_ConfigCollectionExecutor[ConnectionSync]):
    @overload
    def get(self, simple: Literal[False] = False) -> CollectionConfig: ...
    @overload
    def get(self, simple: Literal[True]) -> CollectionConfigSimple: ...
    @overload
    def get(self, simple: bool = False) -> CollectionConfig | CollectionConfigSimple: ...
    def update(
        self,
        *,
        description: Optional[str] = None,
        property_descriptions: Optional[dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigUpdate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            _VectorIndexConfigHNSWUpdate | _VectorIndexConfigFlatUpdate
        ] = None,
        vectorizer_config: Optional[
            _VectorIndexConfigHNSWUpdate
            | _VectorIndexConfigFlatUpdate
            | _VectorIndexConfigDynamicUpdate
            | list[_NamedVectorConfigUpdate]
        ] = None,
        vector_config: Optional[_VectorConfigUpdate | list[_VectorConfigUpdate]] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> None: ...
    def get_shards(self) -> list[ShardStatus]: ...
    def update_shards(
        self, status: Literal["READY", "READONLY"], shard_names: Optional[str | list[str]] = None
    ) -> dict[str, ShardTypes]: ...
    def add_property(self, prop: Property) -> None: ...
    def add_reference(self, ref: ReferenceProperty | _ReferencePropertyMultiTarget) -> None: ...
    @overload
    @deprecated(
        "Using `Configure.NamedVectors` in `vector_config` is deprecated. Instead, use `Configure.Vectors` or `Configure.MultiVectors`."
    )
    def add_vector(
        self, *, vector_config: _NamedVectorConfigCreate | list[_NamedVectorConfigCreate]
    ) -> None: ...
    @overload
    def add_vector(
        self, *, vector_config: _VectorConfigCreate | list[_VectorConfigCreate]
    ) -> None: ...

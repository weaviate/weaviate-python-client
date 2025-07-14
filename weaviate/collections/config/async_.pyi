from typing import Dict, List, Literal, Optional, Union, overload

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
from weaviate.connect.v4 import ConnectionAsync

from .executor import _ConfigCollectionExecutor

class _ConfigCollectionAsync(_ConfigCollectionExecutor[ConnectionAsync]):
    @overload
    async def get(self, simple: Literal[False] = False) -> CollectionConfig: ...
    @overload
    async def get(self, simple: Literal[True]) -> CollectionConfigSimple: ...
    @overload
    async def get(
        self, simple: bool = False
    ) -> Union[CollectionConfig, CollectionConfigSimple]: ...
    async def update(
        self,
        *,
        description: Optional[str] = None,
        property_descriptions: Optional[Dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigUpdate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[_VectorIndexConfigHNSWUpdate, _VectorIndexConfigFlatUpdate]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
        vector_config: Optional[Union[_VectorConfigUpdate, List[_VectorConfigUpdate]]] = None,
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
    @overload
    @deprecated(
        "Using `Configure.NamedVectors` in `vector_config` is deprecated. Instead, use `Configure.Vectors` or `Configure.MultiVectors`."
    )
    async def add_vector(
        self, *, vector_config: Union[_NamedVectorConfigCreate, List[_NamedVectorConfigCreate]]
    ) -> None: ...
    @overload
    async def add_vector(
        self, *, vector_config: Union[_VectorConfigCreate, List[_VectorConfigCreate]]
    ) -> None: ...

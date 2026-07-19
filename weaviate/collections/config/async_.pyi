from typing import Dict, List, Literal, Optional, Sequence, Union, overload

from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    CollectionPropertyIndexes,
    IndexName,
    Property,
    PropertyIndexStatus,
    PropertyIndexTask,
    ReferenceProperty,
    ShardStatus,
    ShardTypes,
    Tokenization,
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
    _VectorIndexConfigHFreshUpdate,
    _VectorIndexConfigHNSWUpdate,
)
from weaviate.collections.classes.config_object_ttl import _ObjectTTLConfigUpdate
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
        object_ttl_config: Optional[_ObjectTTLConfigUpdate] = None,
        replication_config: Optional[_ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigHFreshUpdate,
            ]
        ] = None,
        vectorizer_config: Optional[
            Union[
                _VectorIndexConfigHNSWUpdate,
                _VectorIndexConfigFlatUpdate,
                _VectorIndexConfigDynamicUpdate,
                _VectorIndexConfigHFreshUpdate,
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
    async def delete_property_index(self, property_name: str, index_name: IndexName) -> bool: ...
    @overload
    async def update_property_index(
        self,
        property_name: str,
        index_name: IndexName,
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[Literal["blockmax"]] = None,
        tenants: Optional[Sequence[str]] = None,
        wait_for_completion: Literal[True],
    ) -> PropertyIndexStatus: ...
    @overload
    async def update_property_index(
        self,
        property_name: str,
        index_name: IndexName,
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[Literal["blockmax"]] = None,
        tenants: Optional[Sequence[str]] = None,
        wait_for_completion: Literal[False] = False,
    ) -> PropertyIndexTask: ...
    @overload
    async def rebuild_property_index(
        self,
        property_name: str,
        index_name: IndexName,
        *,
        tenants: Optional[Sequence[str]] = None,
        wait_for_completion: Literal[True],
    ) -> PropertyIndexStatus: ...
    @overload
    async def rebuild_property_index(
        self,
        property_name: str,
        index_name: IndexName,
        *,
        tenants: Optional[Sequence[str]] = None,
        wait_for_completion: Literal[False] = False,
    ) -> PropertyIndexTask: ...
    async def cancel_property_index_task(
        self, property_name: str, index_name: IndexName
    ) -> PropertyIndexTask: ...
    async def get_property_indexes(self) -> CollectionPropertyIndexes: ...

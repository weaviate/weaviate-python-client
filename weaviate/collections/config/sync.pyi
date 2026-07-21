from typing import Dict, List, Literal, Optional, Union, overload

from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    CollectionPropertyIndexes,
    IndexName,
    Property,
    PropertyIndexStatus,
    PropertyIndexTask,
    PropertyIndexType,
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
from weaviate.connect.v4 import ConnectionSync

from .executor import _ConfigCollectionExecutor

class _ConfigCollection(_ConfigCollectionExecutor[ConnectionSync]):
    @overload
    def get(self, simple: Literal[False] = False) -> CollectionConfig: ...
    @overload
    def get(self, simple: Literal[True]) -> CollectionConfigSimple: ...
    @overload
    def get(self, simple: bool = False) -> Union[CollectionConfig, CollectionConfigSimple]: ...
    def update(
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
    @overload
    @deprecated(
        "Using `Configure.NamedVectors` in `vector_config` is deprecated. Instead, use `Configure.Vectors` or `Configure.MultiVectors`."
    )
    def add_vector(
        self, *, vector_config: Union[_NamedVectorConfigCreate, List[_NamedVectorConfigCreate]]
    ) -> None: ...
    @overload
    def add_vector(
        self, *, vector_config: Union[_VectorConfigCreate, List[_VectorConfigCreate]]
    ) -> None: ...
    def delete_property_index(
        self, property_name: str, index_name: Union[PropertyIndexType, IndexName]
    ) -> bool: ...
    @overload
    def update_property_index(
        self,
        property_name: str,
        index_name: Union[PropertyIndexType, IndexName],
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[Literal["blockmax"]] = None,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[True],
    ) -> PropertyIndexStatus: ...
    @overload
    def update_property_index(
        self,
        property_name: str,
        index_name: Union[PropertyIndexType, IndexName],
        *,
        tokenization: Optional[Tokenization] = None,
        algorithm: Optional[Literal["blockmax"]] = None,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[False] = False,
    ) -> PropertyIndexTask: ...
    @overload
    def rebuild_property_index(
        self,
        property_name: str,
        index_name: Union[PropertyIndexType, IndexName],
        *,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[True],
    ) -> PropertyIndexStatus: ...
    @overload
    def rebuild_property_index(
        self,
        property_name: str,
        index_name: Union[PropertyIndexType, IndexName],
        *,
        tenants: Union[List[str], str, None] = None,
        wait_for_completion: Literal[False] = False,
    ) -> PropertyIndexTask: ...
    def cancel_property_index_task(
        self, property_name: str, index_name: Union[PropertyIndexType, IndexName]
    ) -> PropertyIndexTask: ...
    def get_property_indexes(self) -> CollectionPropertyIndexes: ...

from typing import Dict, List, Literal, Optional, Union, overload

from typing_extensions import deprecated

from weaviate.collections.classes.config import (
    CollectionConfig,
    CollectionConfigSimple,
    GenerativeProvider,
    IndexName,
    InvertedIndexConfigUpdate,
    MultiTenancyConfigUpdate,
    Property,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    ReplicationConfigUpdate,
    RerankerProvider,
    ShardStatus,
    ShardTypes,
)
from weaviate.collections.classes.config_named_vectors import (
    _NamedVectorConfigCreate,
    _NamedVectorConfigUpdate,
)
from weaviate.collections.classes.config_object_ttl import ObjectTTLConfigUpdate
from weaviate.collections.classes.config_vector_index import (
    VectorIndexConfigDynamicUpdate,
    VectorIndexConfigFlatUpdate,
    VectorIndexConfigHFreshUpdate,
    VectorIndexConfigHNSWUpdate,
)
from weaviate.collections.classes.config_vectors import VectorConfigCreate, VectorConfigUpdate
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
        inverted_index_config: Optional[InvertedIndexConfigUpdate] = None,
        multi_tenancy_config: Optional[MultiTenancyConfigUpdate] = None,
        object_ttl_config: Optional[ObjectTTLConfigUpdate] = None,
        replication_config: Optional[ReplicationConfigUpdate] = None,
        vector_index_config: Optional[
            Union[
                VectorIndexConfigHNSWUpdate,
                VectorIndexConfigFlatUpdate,
                VectorIndexConfigHFreshUpdate,
            ]
        ] = None,
        vectorizer_config: Optional[
            Union[
                VectorIndexConfigHNSWUpdate,
                VectorIndexConfigFlatUpdate,
                VectorIndexConfigDynamicUpdate,
                VectorIndexConfigHFreshUpdate,
                List[_NamedVectorConfigUpdate],
            ]
        ] = None,
        vector_config: Optional[Union[VectorConfigUpdate, List[VectorConfigUpdate]]] = None,
        generative_config: Optional[GenerativeProvider] = None,
        reranker_config: Optional[RerankerProvider] = None,
    ) -> None: ...
    def get_shards(self) -> List[ShardStatus]: ...
    def update_shards(
        self,
        status: Literal["READY", "READONLY"],
        shard_names: Optional[Union[str, List[str]]] = None,
    ) -> Dict[str, ShardTypes]: ...
    def add_property(self, prop: Property) -> None: ...
    def add_reference(
        self, ref: Union[ReferenceProperty, ReferencePropertyMultiTarget]
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
        self, *, vector_config: Union[VectorConfigCreate, List[VectorConfigCreate]]
    ) -> None: ...
    def delete_property_index(self, property_name: str, index_name: IndexName) -> bool: ...

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
from weaviate.collections.config.config import _ConfigCollectionBase

class _ConvertCollection(_ConfigCollectionBase):
    def convert_to_hnsw(self) -> None: ...
    def convert_to_cagra(self) -> None: ...

import asyncio
from typing import Any, Dict, Generic, List, Literal, Optional, Tuple, Union, cast, overload
from httpx import Response
from pydantic_core import ValidationError
from weaviate.collections.classes.config import (
    _CollectionConfigUpdate,
    _InvertedIndexConfigUpdate,
    _ReplicationConfigUpdate,
    _VectorIndexConfigFlatUpdate,
    PropertyType,
    Property,
    ReferenceProperty,
    _ReferencePropertyMultiTarget,
    _VectorIndexConfigHNSWUpdate,
    CollectionConfig,
    CollectionConfigSimple,
    ShardStatus,
    _ShardStatus,
    ShardTypes,
    _NamedVectorConfigUpdate,
    _MultiTenancyConfigUpdate,
    _GenerativeProvider,
    _RerankerProvider,
)
from weaviate.collections.classes.config_methods import (
    _collection_config_from_json,
    _collection_config_simple_from_json,
)
from weaviate.collections.classes.config_vector_index import _VectorIndexConfigDynamicUpdate
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, ConnectionType
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.util import _decode_json_response_dict, _decode_json_response_list
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings
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
        generative_config: Optional[_GenerativeProvider] = None,
        reranker_config: Optional[_RerankerProvider] = None
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

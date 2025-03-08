import asyncio
from typing import Dict, Any, List, Literal, Optional, Tuple, Union, cast, overload

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
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.exceptions import (
    WeaviateInvalidInputError,
)
from weaviate.util import _decode_json_response_dict, _decode_json_response_list
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings


class _ConvertCollectionBase:
    def __init__(self, connection: ConnectionV4, name: str, tenant: Optional[str]) -> None:
        self._connection = connection
        self._name = name
        self._tenant = tenant

class _ConvertCollectionAsync(_ConvertCollectionBase):
    async def convert_to_hnsw(self) -> None:
        
        path = f"/debug/converttohnsw/index/"+self._name
        obj={}
        
        await self._connection.post(
            path=path,
            weaviate_object=obj,
            error_msg="Index may not have been converted properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Add property to collection"),
            use_debug=True,
        )
    async def convert_to_cagra(self) -> None:
        
        path = f"/debug/converttocagra/index/"+self._name
        obj={}
        
        await self._connection.post(
            path=path,
            weaviate_object=obj,
            error_msg="Index may not have been converted properly.",
            status_codes=_ExpectedStatusCodes(ok_in=200, error="Add property to collection"),
            use_debug=True,
        )
        
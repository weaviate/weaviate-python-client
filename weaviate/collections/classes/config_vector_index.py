from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import Field

from weaviate.collections.classes.config_base import (
    _ConfigCreateModel,
    _ConfigUpdateModel,
    _QuantizerConfigCreate,
    _QuantizerConfigUpdate,
)

from weaviate.collections.classes.config_vectorizers import VectorDistances


class VectorIndexType(str, Enum):
    """The available vector index types in Weaviate.

    Attributes:
        HNSW: Hierarchical Navigable Small World (HNSW) index.
        FLAT: Flat index.
    """

    HNSW = "hnsw"
    FLAT = "flat"


class _VectorIndexConfigCreate(_ConfigCreateModel):
    distance: Optional[VectorDistances]
    vectorCacheMaxObjects: Optional[int]
    quantizer: Optional[_QuantizerConfigCreate] = Field(exclude=True)

    @staticmethod
    @abstractmethod
    def vector_index_type() -> VectorIndexType:
        ...

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.quantizer is not None:
            ret_dict[self.quantizer.quantizer_name()] = self.quantizer._to_dict()
        if self.distance is not None:
            ret_dict["distance"] = str(self.distance.value)

        return ret_dict


class _VectorIndexConfigUpdate(_ConfigUpdateModel):
    vectorCacheMaxObjects: Optional[int]
    quantizer: Optional[_QuantizerConfigUpdate] = Field(exclude=True)

    @staticmethod
    @abstractmethod
    def vector_index_type() -> VectorIndexType:
        ...

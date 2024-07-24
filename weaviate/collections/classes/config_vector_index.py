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
    DYNAMIC = "dynamic"


class _VectorIndexConfigCreate(_ConfigCreateModel):
    distance: Optional[VectorDistances]
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
    quantizer: Optional[_QuantizerConfigUpdate] = Field(exclude=True)

    @staticmethod
    @abstractmethod
    def vector_index_type() -> VectorIndexType:
        ...


class _VectorIndexConfigSkipCreate(_VectorIndexConfigCreate):
    skip: bool = True

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.HNSW


class _VectorIndexConfigHNSWCreate(_VectorIndexConfigCreate):
    cleanupIntervalSeconds: Optional[int]
    dynamicEfMin: Optional[int]
    dynamicEfMax: Optional[int]
    dynamicEfFactor: Optional[int]
    efConstruction: Optional[int]
    ef: Optional[int]
    flatSearchCutoff: Optional[int]
    maxConnections: Optional[int]
    vectorCacheMaxObjects: Optional[int]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.HNSW


class _VectorIndexConfigFlatCreate(_VectorIndexConfigCreate):
    vectorCacheMaxObjects: Optional[int]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.FLAT


class _VectorIndexConfigHNSWUpdate(_VectorIndexConfigUpdate):
    dynamicEfMin: Optional[int]
    dynamicEfMax: Optional[int]
    dynamicEfFactor: Optional[int]
    ef: Optional[int]
    flatSearchCutoff: Optional[int]
    vectorCacheMaxObjects: Optional[int]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.HNSW


class _VectorIndexConfigFlatUpdate(_VectorIndexConfigUpdate):
    vectorCacheMaxObjects: Optional[int]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.FLAT


class _VectorIndexConfigDynamicCreate(_VectorIndexConfigCreate):
    threshold: Optional[int]
    hnsw: Optional[_VectorIndexConfigHNSWCreate]
    flat: Optional[_VectorIndexConfigFlatCreate]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.DYNAMIC

    def _to_dict(self) -> dict:
        ret_dict = super()._to_dict()
        if self.hnsw is not None:
            ret_dict["hnsw"] = self.hnsw._to_dict()
        if self.flat is not None:
            ret_dict["flat"] = self.flat._to_dict()
        if self.threshold is not None:
            ret_dict["threshold"] = self.threshold

        return ret_dict


class _VectorIndexConfigDynamicUpdate(_VectorIndexConfigUpdate):
    threshold: Optional[int]
    hnsw: Optional[_VectorIndexConfigHNSWUpdate]
    flat: Optional[_VectorIndexConfigFlatUpdate]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.DYNAMIC

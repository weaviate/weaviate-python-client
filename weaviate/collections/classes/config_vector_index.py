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


class VectorFilterStrategy(str, Enum):
    """Set the strategy when doing a filtered HNSW search.

    Attributes:
        SWEEPING: Do normal ANN search and skip nodes.
        ACORN: Multi-hop search to find new candidates matching the filter.
    """

    SWEEPING = "sweeping"
    ACORN = "acorn"


class VectorIndexType(str, Enum):
    """The available vector index types in Weaviate.

    Attributes:
        HNSW: Hierarchical Navigable Small World (HNSW) index.
        FLAT: Flat index.
        DYNAMIC: Dynamic index that switches between HNSW and FLAT.
        CUVS: CUDA Vector Search index.
    """

    HNSW = "hnsw"
    FLAT = "flat"
    DYNAMIC = "dynamic"
    CUVS = "cuvs"


class CUVSBuildAlgo(str, Enum):
    """The available build algorithms for CUVS index.

    Attributes:
        NN_DESCENT: Nearest Neighbor Descent algorithm.
        IVF_PQ: Inverted File with Product Quantization.
        AUTO_SELECT: Automatically select the best algorithm.
    """

    NN_DESCENT = "nn_descent"
    IVF_PQ = "ivf_pq"
    AUTO_SELECT = "auto_select"


class CUVSSearchAlgo(str, Enum):
    """The available search algorithms for CUVS index.

    Attributes:
        MULTI_CTA: Multi-CTA search algorithm.
        SINGLE_CTA: Single-CTA search algorithm.
    """

    MULTI_CTA = "multi_cta"
    SINGLE_CTA = "single_cta"


class CUVSIndexLocation(str, Enum):
    """Whether the index is on the GPU (CAGRA) or CPU (HNSW).
    """

    GPU = "gpu"
    CPU = "cpu"



class _MultiVectorConfigCreateBase(_ConfigCreateModel):
    enabled: bool = Field(default=True)


class _MultiVectorConfigCreate(_MultiVectorConfigCreateBase):
    aggregation: Optional[str]



class _VectorIndexConfigCreate(_ConfigCreateModel):
    distance: Optional[VectorDistances]
    multivector: Optional[_MultiVectorConfigCreate]
    quantizer: Optional[_QuantizerConfigCreate] = Field(exclude=True)

    @staticmethod
    @abstractmethod
    def vector_index_type() -> VectorIndexType: ...

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
    def vector_index_type() -> VectorIndexType: ...


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
    filterStrategy: Optional[VectorFilterStrategy]
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
    filterStrategy: Optional[VectorFilterStrategy]
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


class _VectorIndexConfigCUVSCreate(_VectorIndexConfigCreate):
    """Configuration for creating a CUVS (CUDA Vector Search) index."""

    graphDegree: Optional[int] = Field(default=32)
    intermediateGraphDegree: Optional[int] = Field(default=32)
    buildAlgo: Optional[CUVSBuildAlgo] = Field(default=CUVSBuildAlgo.NN_DESCENT)
    searchAlgo: Optional[CUVSSearchAlgo] = Field(default=CUVSSearchAlgo.MULTI_CTA)
    itopKSize: Optional[int] = Field(default=256)
    searchWidth: Optional[int] = Field(default=1)
    indexLocation: Optional[CUVSIndexLocation] = Field(default=CUVSIndexLocation.GPU)

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.CUVS


class _VectorIndexConfigCUVSUpdate(_VectorIndexConfigUpdate):
    """Configuration for updating a CUVS (CUDA Vector Search) index."""

    graphDegree: Optional[int] = None
    intermediateGraphDegree: Optional[int] = None
    buildAlgo: Optional[CUVSBuildAlgo] = None
    searchAlgo: Optional[CUVSSearchAlgo] = None
    itopKSize: Optional[int] = None
    searchWidth: Optional[int] = None
    indexLocation: Optional[CUVSIndexLocation]

    @staticmethod
    def vector_index_type() -> VectorIndexType:
        return VectorIndexType.CUVS


VectorIndexConfigCUVS = _VectorIndexConfigCUVSCreate

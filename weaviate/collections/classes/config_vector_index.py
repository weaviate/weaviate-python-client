from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, overload

from pydantic import Field
from typing_extensions import deprecated

from weaviate.collections.classes.config_base import (
    _ConfigCreateModel,
    _ConfigUpdateModel,
    _QuantizerConfigCreate,
    _QuantizerConfigUpdate,
)
from weaviate.collections.classes.config_vectorizers import VectorDistances
from weaviate.str_enum import BaseEnum
from weaviate.warnings import _Warnings


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
    """

    HNSW = "hnsw"
    FLAT = "flat"
    DYNAMIC = "dynamic"


class _MultiVectorConfigCreateBase(_ConfigCreateModel):
    enabled: bool = Field(default=True)


class _MultiVectorEncodingConfigCreate(_MultiVectorConfigCreateBase):
    enabled: bool = Field(default=True)

    @staticmethod
    @abstractmethod
    def encoding_name() -> str: ...


class _MuveraConfigCreate(_MultiVectorEncodingConfigCreate):
    ksim: Optional[int]
    dprojections: Optional[int]
    repetitions: Optional[int]

    @staticmethod
    def encoding_name() -> str:
        return "muvera"


class _MultiVectorConfigCreate(_MultiVectorConfigCreateBase):
    encoding: Optional[_MultiVectorEncodingConfigCreate] = Field(exclude=True)
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
            if isinstance(self.quantizer, _UncompressedConfigCreate):
                ret_dict[self.quantizer.quantizer_name()] = True
            else:
                ret_dict[self.quantizer.quantizer_name()] = self.quantizer._to_dict()
        if self.distance is not None:
            ret_dict["distance"] = str(self.distance.value)
        if self.multivector is not None and self.multivector.encoding is not None:
            ret_dict["multivector"][self.multivector.encoding.encoding_name()] = (
                self.multivector.encoding._to_dict()
            )

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


class PQEncoderType(str, BaseEnum):
    """Type of the PQ encoder.

    Attributes:
        KMEANS: K-means encoder.
        TILE: Tile encoder.
    """

    KMEANS = "kmeans"
    TILE = "tile"


class PQEncoderDistribution(str, BaseEnum):
    """Distribution of the PQ encoder.

    Attributes:
        LOG_NORMAL: Log-normal distribution.
        NORMAL: Normal distribution.
    """

    LOG_NORMAL = "log-normal"
    NORMAL = "normal"


class MultiVectorAggregation(str, BaseEnum):
    """Aggregation type to use for multivector indices.

    Attributes:
        MAX_SIM: Maximum similarity.
    """

    MAX_SIM = "maxSim"


class _PQEncoderConfigCreate(_ConfigCreateModel):
    type_: Optional[PQEncoderType] = Field(serialization_alias="type")
    distribution: Optional[PQEncoderDistribution]


class _PQEncoderConfigUpdate(_ConfigUpdateModel):
    type_: Optional[PQEncoderType]
    distribution: Optional[PQEncoderDistribution]

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Must be done manually since Pydantic does not work well with type and type_.

        Errors shadowing type occur if we want to use type as a field name.
        """
        if self.type_ is not None:
            schema["type"] = str(self.type_.value)
        if self.distribution is not None:
            schema["distribution"] = str(self.distribution.value)
        return schema


class _PQConfigCreate(_QuantizerConfigCreate):
    bitCompression: Optional[bool] = Field(default=None)
    centroids: Optional[int]
    encoder: _PQEncoderConfigCreate
    segments: Optional[int]
    trainingLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "pq"


class _BQConfigCreate(_QuantizerConfigCreate):
    cache: Optional[bool]
    rescoreLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "bq"


class _SQConfigCreate(_QuantizerConfigCreate):
    cache: Optional[bool]
    rescoreLimit: Optional[int]
    trainingLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "sq"


class _RQConfigCreate(_QuantizerConfigCreate):
    bits: Optional[int]
    rescoreLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "rq"


class _UncompressedConfigCreate(_QuantizerConfigCreate):
    @staticmethod
    def quantizer_name() -> str:
        return "skipDefaultQuantization"


class _PQConfigUpdate(_QuantizerConfigUpdate):
    bitCompression: Optional[bool] = Field(default=None)
    centroids: Optional[int]
    enabled: Optional[bool]
    segments: Optional[int]
    trainingLimit: Optional[int]
    encoder: Optional[_PQEncoderConfigUpdate]

    @staticmethod
    def quantizer_name() -> str:
        return "pq"


class _BQConfigUpdate(_QuantizerConfigUpdate):
    enabled: Optional[bool]
    rescoreLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "bq"


class _RQConfigUpdate(_QuantizerConfigUpdate):
    enabled: Optional[bool]
    rescoreLimit: Optional[int]
    bits: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "rq"


class _SQConfigUpdate(_QuantizerConfigUpdate):
    enabled: Optional[bool]
    rescoreLimit: Optional[int]
    trainingLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "sq"


class _VectorIndexMultivectorEncoding:
    @staticmethod
    def muvera(
        ksim: Optional[int] = None,
        dprojections: Optional[int] = None,
        repetitions: Optional[int] = None,
    ) -> _MultiVectorEncodingConfigCreate:
        return _MuveraConfigCreate(
            enabled=True,
            ksim=ksim,
            dprojections=dprojections,
            repetitions=repetitions,
        )


class _VectorIndexMultiVector:
    Encoding = _VectorIndexMultivectorEncoding

    @deprecated(
        'Using the "encoding" argument is deprecated. Instead, specify it at the top-level when creating your `vector_config`'
    )
    @overload
    @staticmethod
    def multi_vector(
        encoding: _MultiVectorEncodingConfigCreate,
        aggregation: Optional[MultiVectorAggregation] = None,
    ) -> _MultiVectorConfigCreate: ...

    @overload
    @staticmethod
    def multi_vector(
        encoding: Optional[_MultiVectorEncodingConfigCreate] = None,
        aggregation: Optional[MultiVectorAggregation] = None,
    ) -> _MultiVectorConfigCreate: ...

    @staticmethod
    def multi_vector(
        encoding: Optional[_MultiVectorEncodingConfigCreate] = None,
        aggregation: Optional[MultiVectorAggregation] = None,
    ) -> _MultiVectorConfigCreate:
        if encoding is not None:
            _Warnings.encoding_in_multi_vector_config()
        return _MultiVectorConfigCreate(
            encoding=encoding if encoding is not None else None,
            aggregation=aggregation.value if aggregation is not None else None,
        )


class _VectorIndexQuantizer:
    @staticmethod
    def pq(
        bit_compression: Optional[bool] = None,
        centroids: Optional[int] = None,
        encoder_distribution: Optional[PQEncoderDistribution] = None,
        encoder_type: Optional[PQEncoderType] = None,
        segments: Optional[int] = None,
        training_limit: Optional[int] = None,
    ) -> _PQConfigCreate:
        """Create a `_PQConfigCreate` object to be used when defining the product quantization (PQ) configuration of Weaviate.

        Use this method when defining the `quantizer` argument in the `vector_index` configuration.

        Args:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#hnsw-with-compression) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        if bit_compression is not None:
            _Warnings.bit_compression_in_pq_config()
        return _PQConfigCreate(
            centroids=centroids,
            segments=segments,
            trainingLimit=training_limit,
            encoder=_PQEncoderConfigCreate(type_=encoder_type, distribution=encoder_distribution),
        )

    @staticmethod
    def bq(
        cache: Optional[bool] = None,
        rescore_limit: Optional[int] = None,
    ) -> _BQConfigCreate:
        """Create a `_BQConfigCreate` object to be used when defining the binary quantization (BQ) configuration of Weaviate.

        Use this method when defining the `quantizer` argument in the `vector_index` configuration. Note that the arguments have no effect for HNSW.

        Args:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#binary-quantization) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _BQConfigCreate(
            cache=cache,
            rescoreLimit=rescore_limit,
        )

    @staticmethod
    def sq(
        cache: Optional[bool] = None,
        rescore_limit: Optional[int] = None,
        training_limit: Optional[int] = None,
    ) -> _SQConfigCreate:
        """Create a `_SQConfigCreate` object to be used when defining the scalar quantization (SQ) configuration of Weaviate.

        Use this method when defining the `quantizer` argument in the `vector_index` configuration. Note that the arguments have no effect for HNSW.

        Args:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#binary-quantization) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _SQConfigCreate(
            cache=cache,
            rescoreLimit=rescore_limit,
            trainingLimit=training_limit,
        )

    @staticmethod
    def rq(
        bits: Optional[int] = None,
        rescore_limit: Optional[int] = None,
    ) -> _RQConfigCreate:
        """Create a `_RQConfigCreate` object to be used when defining the Rotational quantization (RQ) configuration of Weaviate.

        Use this method when defining the `quantizer` argument in the `vector_index` configuration. Note that the arguments have no effect for HNSW.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _RQConfigCreate(
            bits=bits,
            rescoreLimit=rescore_limit,
        )

    @staticmethod
    def none() -> _UncompressedConfigCreate:
        """Create a a vector index without compression."""
        return _UncompressedConfigCreate()


class _VectorIndex:
    MultiVector = _VectorIndexMultiVector
    Quantizer = _VectorIndexQuantizer

    @staticmethod
    def none() -> _VectorIndexConfigSkipCreate:
        """Create a `_VectorIndexConfigSkipCreate` object to be used when configuring Weaviate to not index your vectors.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.
        """
        return _VectorIndexConfigSkipCreate(
            distance=None,
            quantizer=None,
            multivector=None,
        )

    @overload
    @staticmethod
    @deprecated(
        'Using the "multi_vector" argument is deprecated. Instead, specify it at the top-level in `multi_vector_index_config` when creating your `vector_config` with `MultiVectors.module()`'
    )
    def hnsw(
        cleanup_interval_seconds: Optional[int] = None,
        distance_metric: Optional[VectorDistances] = None,
        dynamic_ef_factor: Optional[int] = None,
        dynamic_ef_max: Optional[int] = None,
        dynamic_ef_min: Optional[int] = None,
        ef: Optional[int] = None,
        ef_construction: Optional[int] = None,
        filter_strategy: Optional[VectorFilterStrategy] = None,
        flat_search_cutoff: Optional[int] = None,
        max_connections: Optional[int] = None,
        vector_cache_max_objects: Optional[int] = None,
        *,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        multi_vector: _MultiVectorConfigCreate,
    ) -> _VectorIndexConfigHNSWCreate: ...

    @overload
    @staticmethod
    def hnsw(
        cleanup_interval_seconds: Optional[int] = None,
        distance_metric: Optional[VectorDistances] = None,
        dynamic_ef_factor: Optional[int] = None,
        dynamic_ef_max: Optional[int] = None,
        dynamic_ef_min: Optional[int] = None,
        ef: Optional[int] = None,
        ef_construction: Optional[int] = None,
        filter_strategy: Optional[VectorFilterStrategy] = None,
        flat_search_cutoff: Optional[int] = None,
        max_connections: Optional[int] = None,
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        multi_vector: Optional[_MultiVectorConfigCreate] = None,
    ) -> _VectorIndexConfigHNSWCreate: ...

    @staticmethod
    def hnsw(
        cleanup_interval_seconds: Optional[int] = None,
        distance_metric: Optional[VectorDistances] = None,
        dynamic_ef_factor: Optional[int] = None,
        dynamic_ef_max: Optional[int] = None,
        dynamic_ef_min: Optional[int] = None,
        ef: Optional[int] = None,
        ef_construction: Optional[int] = None,
        filter_strategy: Optional[VectorFilterStrategy] = None,
        flat_search_cutoff: Optional[int] = None,
        max_connections: Optional[int] = None,
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        multi_vector: Optional[_MultiVectorConfigCreate] = None,
    ) -> _VectorIndexConfigHNSWCreate:
        """Create a `_VectorIndexConfigHNSWCreate` object to be used when defining the HNSW vector index configuration of Weaviate.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.

        Args:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        if multi_vector is not None:
            _Warnings.multi_vector_in_hnsw_config()
        return _VectorIndexConfigHNSWCreate(
            cleanupIntervalSeconds=cleanup_interval_seconds,
            distance=distance_metric,
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            dynamicEfFactor=dynamic_ef_factor,
            efConstruction=ef_construction,
            ef=ef,
            filterStrategy=filter_strategy,
            flatSearchCutoff=flat_search_cutoff,
            maxConnections=max_connections,
            vectorCacheMaxObjects=vector_cache_max_objects,
            quantizer=quantizer,
            multivector=multi_vector,
        )

    @staticmethod
    def flat(
        distance_metric: Optional[VectorDistances] = None,
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
    ) -> _VectorIndexConfigFlatCreate:
        """Create a `_VectorIndexConfigFlatCreate` object to be used when defining the FLAT vector index configuration of Weaviate.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.

        Args:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigFlatCreate(
            distance=distance_metric,
            vectorCacheMaxObjects=vector_cache_max_objects,
            quantizer=quantizer,
            multivector=None,
        )

    @staticmethod
    def dynamic(
        distance_metric: Optional[VectorDistances] = None,
        threshold: Optional[int] = None,
        hnsw: Optional[_VectorIndexConfigHNSWCreate] = None,
        flat: Optional[_VectorIndexConfigFlatCreate] = None,
    ) -> _VectorIndexConfigDynamicCreate:
        """Create a `_VectorIndexConfigDynamicCreate` object to be used when defining the DYNAMIC vector index configuration of Weaviate.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.

        Args:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigDynamicCreate(
            distance=distance_metric,
            threshold=threshold,
            hnsw=hnsw,
            flat=flat,
            quantizer=None,
            multivector=None,
        )

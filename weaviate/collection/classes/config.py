from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from weaviate.util import _capitalize_first_letter
from weaviate.warnings import _Warnings


class ConsistencyLevel(str, Enum):
    ALL = "ALL"
    ONE = "ONE"
    QUORUM = "QUORUM"


class DataType(str, Enum):
    TEXT = "text"
    TEXT_ARRAY = "text[]"
    INT = "int"
    INT_ARRAY = "int[]"
    BOOL = "boolean"
    BOOL_ARRAY = "boolean[]"
    NUMBER = "number"
    NUMBER_ARRAY = "number[]"
    DATE = "date"
    DATE_ARRAY = "date[]"
    UUID = "uuid"
    UUID_ARRAY = "uuid[]"
    GEO_COORDINATES = "geoCoordinates"
    BLOB = "blob"
    PHONE_NUMBER = "phoneNumber"


class VectorIndexType(str, Enum):
    HNSW = "hnsw"


class Tokenization(str, Enum):
    WORD = "word"
    WHITESPACE = "whitespace"
    LOWERCASE = "lowercase"
    FIELD = "field"


class Vectorizer(str, Enum):
    NONE = "none"
    TEXT2VEC_OPENAI = "text2vec-openai"
    TEXT2VEC_COHERE = "text2vec-cohere"
    TEXT2VEC_PALM = "text2vec-palm"
    TEXT2VEC_HUGGINGFACE = "text2vec-huggingface"
    TEXT2VEC_TRANSFORMERS = "text2vec-transformers"
    TEXT2VEC_CONTEXTIONARY = "text2vec-contextionary"
    TEXT2VEC_GPT4ALL = "text2vec-gpt4all"
    IMG2VEC_NEURAL = "img2vec-neural"
    MULTI2VEC_CLIP = "multi2vec-clip"
    MULTI2VEC_BIND = "multi2vec-bind"
    REF2VEC_CENTROID = "ref2vec-centroid"


class GenerativeSearches(str, Enum):
    OPENAI = "generative-openai"
    COHERE = "generative-cohere"
    PALM = "generative-palm"


class VectorDistance(str, Enum):
    COSINE = "cosine"
    DOT = "dot"
    L2_SQUARED = "l2-squared"
    HAMMING = "hamming"
    MANHATTAN = "manhattan"


class StopwordsPreset(str, Enum):
    NONE = "none"
    EN = "en"


class PQEncoderType(str, Enum):
    KMEANS = "kmeans"
    TILE = "tile"


class PQEncoderDistribution(str, Enum):
    LOG_NORMAL = "log-normal"
    NORMAL = "normal"


class ConfigCreateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def to_dict(self) -> Dict[str, Any]:
        return cast(dict, self.model_dump(exclude_none=True))


class ConfigUpdateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if val is None:
                continue
            if isinstance(val, Enum):
                schema[cls_field] = str(val.value)
            elif isinstance(val, (int, float, bool, str, list)):
                schema[cls_field] = val
            else:
                assert isinstance(val, ConfigUpdateModel)
                schema[cls_field] = val.merge_with_existing(schema[cls_field])
        return schema


class PQEncoderConfigCreate(ConfigCreateModel):
    type_: PQEncoderType = Field(default=PQEncoderType.KMEANS)
    distribution: PQEncoderDistribution = Field(default=PQEncoderDistribution.LOG_NORMAL)

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["type"] = ret_dict.pop("type_")
        return ret_dict


class PQEncoderConfigUpdate(ConfigUpdateModel):
    type_: Optional[PQEncoderType] = None
    distribution: Optional[PQEncoderDistribution] = None

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Must be done manually since Pydantic does not work well with type and type_.
        Errors shadowing type occur if we want to use type as a field name.
        """
        if self.type_ is not None:
            schema["type"] = str(self.type_.value)
        if self.distribution is not None:
            schema["distribution"] = str(self.distribution.value)
        return schema


class PQConfigCreate(ConfigCreateModel):
    bitCompression: bool
    centroids: int
    enabled: bool
    encoder: PQEncoderConfigCreate
    segments: int
    trainingLimit: int

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["encoder"] = {
            "type": ret_dict.pop("encoder_type"),
            "distribution": ret_dict.pop("encoder_distribution"),
        }
        return ret_dict


class PQConfigUpdate(ConfigUpdateModel):
    bitCompression: Optional[bool]
    centroids: Optional[int]
    enabled: Optional[bool]
    segments: Optional[int]
    trainingLimit: Optional[int]
    encoder: Optional[PQEncoderConfigUpdate]


class VectorIndexConfigCreate(ConfigCreateModel):
    cleanupIntervalSeconds: int
    distance: VectorDistance
    dynamicEfMin: int
    dynamicEfMax: int
    dynamicEfFactor: int
    efConstruction: int
    ef: int
    flatSearchCutoff: int
    maxConnections: int
    pq: PQConfigCreate
    skip: bool
    vectorCacheMaxObjects: int


class VectorIndexConfigUpdate(ConfigUpdateModel):
    dynamicEfFactor: Optional[int]
    dynamicEfMin: Optional[int]
    dynamicEfMax: Optional[int]
    ef: Optional[int]
    flatSearchCutoff: Optional[int]
    skip: Optional[bool]
    vectorCacheMaxObjects: Optional[int]
    pq: Optional[PQConfigUpdate]


class VectorIndexConfig:
    @classmethod
    def create(
        cls,
        cleanup_interval_seconds: int = 300,
        distance_metric: VectorDistance = VectorDistance.COSINE,
        dynamic_ef_min: int = 100,
        dynamic_ef_max: int = 500,
        dynamic_ef_factor: int = 8,
        ef_construction: int = 128,
        ef: int = -1,
        flat_search_cutoff: int = 40000,
        max_connections: int = 64,
        pq_bit_compression: bool = False,
        pq_centroids: int = 256,
        pq_enabled: bool = False,
        pq_encoder_distribution: PQEncoderDistribution = PQEncoderDistribution.LOG_NORMAL,
        pq_encoder_type: PQEncoderType = PQEncoderType.KMEANS,
        pq_segments: int = 0,
        pq_training_limit: int = 10000,
        skip: bool = False,
        vector_cache_max_objects: int = 1000000000000,
    ) -> VectorIndexConfigCreate:
        return VectorIndexConfigCreate(
            cleanupIntervalSeconds=cleanup_interval_seconds,
            distance=distance_metric,
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            dynamicEfFactor=dynamic_ef_factor,
            efConstruction=ef_construction,
            ef=ef,
            flatSearchCutoff=flat_search_cutoff,
            maxConnections=max_connections,
            pq=PQConfigCreate(
                bitCompression=pq_bit_compression,
                centroids=pq_centroids,
                enabled=pq_enabled,
                encoder=PQEncoderConfigCreate(
                    type_=pq_encoder_type,
                    distribution=pq_encoder_distribution,
                ),
                segments=pq_segments,
                trainingLimit=pq_training_limit,
            ),
            skip=skip,
            vectorCacheMaxObjects=vector_cache_max_objects,
        )

    @classmethod
    def update(
        cls,
        dynamic_ef_factor: Optional[int] = None,
        dynamic_ef_min: Optional[int] = None,
        dynamic_ef_max: Optional[int] = None,
        ef: Optional[int] = None,
        flat_search_cutoff: Optional[int] = None,
        skip: Optional[bool] = None,
        vector_cache_max_objects: Optional[int] = None,
        pq_bit_compression: Optional[bool] = None,
        pq_centroids: Optional[int] = None,
        pq_enabled: Optional[bool] = None,
        pq_encoder_distribution: Optional[PQEncoderDistribution] = None,
        pq_encoder_type: Optional[PQEncoderType] = None,
        pq_segments: Optional[int] = None,
        pq_training_limit: Optional[int] = None,
    ) -> VectorIndexConfigUpdate:
        return VectorIndexConfigUpdate(
            dynamicEfFactor=dynamic_ef_factor,
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            ef=ef,
            flatSearchCutoff=flat_search_cutoff,
            skip=skip,
            vectorCacheMaxObjects=vector_cache_max_objects,
            pq=PQConfigUpdate(
                bitCompression=pq_bit_compression,
                centroids=pq_centroids,
                enabled=pq_enabled,
                encoder=PQEncoderConfigUpdate(
                    type_=pq_encoder_type,
                    distribution=pq_encoder_distribution,
                ),
                segments=pq_segments,
                trainingLimit=pq_training_limit,
            ),
        )


class ShardingConfigCreate(ConfigCreateModel):
    virtualPerPhysical: int
    desiredCount: int
    actualCount: int
    desiredVirtualCount: int
    actualVirtualCount: int
    key: str = "_id"
    strategy: str = "hash"
    function: str = "murmur3"


class ShardingConfig:
    """This class has no `.update()` method because you cannot update the sharding configuration of Weaviate dynamically"""

    @classmethod
    def create(
        cls,
        virtual_per_physical: int = 128,
        desired_count: int = 1,
        actual_count: int = 1,
        desired_virtual_count: int = 128,
        actual_virtual_count: int = 128,
    ) -> ShardingConfigCreate:
        """Create a `ShardingConfigCreate` object to be used when defining the sharding configuration of Weaviate.

        Args:
            `virtual_per_physical`: The number of virtual shards per physical shard. Defaults to `128`.
            `desired_count`: The desired number of physical shards. Defaults to `1`.
            `actual_count`: The actual number of physical shards. Defaults to `1`.
            `desired_virtual_count`: The desired number of virtual shards. Defaults to `128`.
            `actual_virtual_count`: The actual number of virtual shards. Defaults to `128`.

        Returns:
            A `ShardingConfigCreate` object.
        """
        return ShardingConfigCreate(
            virtualPerPhysical=virtual_per_physical,
            desiredCount=desired_count,
            actualCount=actual_count,
            desiredVirtualCount=desired_virtual_count,
            actualVirtualCount=actual_virtual_count,
        )


class ReplicationConfigCreate(ConfigCreateModel):
    factor: int


class ReplicationConfigUpdate(ConfigUpdateModel):
    factor: Optional[int]


class ReplicationConfig:
    @classmethod
    def create(cls, factor: int = 1) -> ReplicationConfigCreate:
        """Create a `ReplicationConfigCreate` object to be used when defining the replication configuration of Weaviate.

        Args:
            `factor`: The replication factor. Defaults to `1`.

        Returns:
            A `ReplicationConfigCreate` object.
        """
        return ReplicationConfigCreate(factor=factor)

    @classmethod
    def update(cls, factor: int = 1) -> ReplicationConfigUpdate:
        """Create a `ReplicationConfigUpdate` object.

        Args:
            `factor`: The replication factor. Defaults to `1`.

        Returns:
            A `ReplicationConfigUpdate` object.
        """
        return ReplicationConfigUpdate(factor=factor)


class BM25ConfigCreate(ConfigCreateModel):
    b: float
    k1: float


class BM25ConfigUpdate(ConfigUpdateModel):
    b: Optional[float]
    k1: Optional[float]


class StopwordsCreate(ConfigCreateModel):
    preset: Optional[StopwordsPreset]
    additions: Optional[List[str]]
    removals: Optional[List[str]]


class StopwordsUpdate(ConfigUpdateModel):
    preset: Optional[StopwordsPreset]
    additions: Optional[List[str]]
    removals: Optional[List[str]]


class InvertedIndexConfigCreate(ConfigCreateModel):
    bm25: BM25ConfigCreate
    cleanupIntervalSeconds: int
    indexTimestamps: bool
    indexPropertyLength: bool
    indexNullState: bool
    stopwords: StopwordsCreate


class InvertedIndexConfigUpdate(ConfigUpdateModel):
    bm25: Optional[BM25ConfigUpdate]
    cleanupIntervalSeconds: Optional[int]
    indexTimestamps: Optional[bool]
    indexPropertyLength: Optional[bool]
    indexNullState: Optional[bool]
    stopwords: Optional[StopwordsUpdate]


class InvertedIndexConfig:
    @classmethod
    def create(
        cls,
        bm25_b: float = 0.75,
        bm25_k1: float = 1.2,
        cleanup_interval_seconds: int = 60,
        index_timestamps: bool = False,
        index_property_length: bool = False,
        index_null_state: bool = False,
        stopwords_preset: Optional[StopwordsPreset] = None,
        stopwords_additions: Optional[List[str]] = None,
        stopwords_removals: Optional[List[str]] = None,
    ) -> InvertedIndexConfigCreate:
        """Create an `InvertedIndexConfigCreate` object to be used when defining the configuration of the keyword searching algorithm of Weaviate.

        Define the free parameters of the BM25 ranking algorithm through `bm25_b` and `bm25_k1`. The default values are
        `bm25_b=0.75` and `bm25_k1=1.2`. See the [documentation](https://weaviate.io/developers/weaviate/search/bm25) for detail on the
        BM25 implementation and the [Wikipedia article](https://en.wikipedia.org/wiki/Okapi_BM25) for details on the theory, especially
        in relation to the `bm25_b` and `bm25_k1` parameters.

        Args:
            `bm25_b`: The `b` parameter of the BM25 ranking algorithm. Defaults to `0.75`.
            `bm25_k1`: The `k1` parameter of the BM25 ranking algorithm. Defaults to `1.2`.
            `cleanup_interval_seconds`: The interval in seconds at which the inverted index is cleaned up. Defaults to `60`.
            `index_timestamps`: Whether to index timestamps. Defaults to `False`.
            `index_property_length`: Whether to index property length. Defaults to `None`.
            `index_null_state`: Whether to index the null state. Defaults to `None`.
            `stopwords_preset`: The preset to use for stopwords. Defaults to `None`.
            `stopwords_additions`: The stopwords to add. Defaults to `None`.
            `stopwords_removals`: The stopwords to remove. Defaults to `None`.

        Returns:
            An `InvertedIndexConfigCreate` object.
        """
        return InvertedIndexConfigCreate(
            bm25=BM25ConfigCreate(b=bm25_b, k1=bm25_k1),
            cleanupIntervalSeconds=cleanup_interval_seconds,
            indexTimestamps=index_timestamps,
            indexPropertyLength=index_property_length,
            indexNullState=index_null_state,
            stopwords=StopwordsCreate(
                preset=stopwords_preset,
                additions=stopwords_additions,
                removals=stopwords_removals,
            ),
        )

    @classmethod
    def update(
        cls,
        bm25_b: Optional[float] = None,
        bm25_k1: Optional[float] = None,
        cleanup_interval_seconds: Optional[int] = None,
        index_timestamps: Optional[bool] = None,
        index_property_length: Optional[bool] = None,
        index_null_state: Optional[bool] = None,
        stopwords_preset: Optional[StopwordsPreset] = None,
        stopwords_additions: Optional[List[str]] = None,
        stopwords_removals: Optional[List[str]] = None,
    ) -> InvertedIndexConfigUpdate:
        """Create an `InvertedIndexConfigUpdate` object.

        Args:
            `bm25_b`: The `b` parameter of the BM25 ranking algorithm. Defaults to `None`.
            `bm25_k1`: The `k1` parameter of the BM25 ranking algorithm. Defaults to `None`.
            `cleanup_interval_seconds`: The interval in seconds at which the inverted index is cleaned up. Defaults to `None`.
            `index_timestamps`: Whether to index timestamps. Defaults to `None`.
            `index_property_length`: Whether to index property length. Defaults to `None`.
            `index_null_state`: Whether to index the null state. Defaults to `None`.
            `stopwords_preset`: The preset to use for stopwords. Defaults to `None`.
            `stopwords_additions`: The stopwords to add. Defaults to `None`.
            `stopwords_removals`: The stopwords to remove. Defaults to `None`.

        Returns:
            An `InvertedIndexConfigUpdate` object.
        """
        return InvertedIndexConfigUpdate(
            bm25=BM25ConfigUpdate(b=bm25_b, k1=bm25_k1),
            cleanupIntervalSeconds=cleanup_interval_seconds,
            indexTimestamps=index_timestamps,
            indexPropertyLength=index_property_length,
            indexNullState=index_null_state,
            stopwords=StopwordsUpdate(
                preset=stopwords_preset,
                additions=stopwords_additions,
                removals=stopwords_removals,
            ),
        )


class MultiTenancyConfigCreate(ConfigCreateModel):
    enabled: bool = False


class MultiTenancyConfigUpdate(ConfigUpdateModel):
    enabled: Optional[bool] = None


class MultiTenancyConfig:
    @classmethod
    def create(cls, enabled: bool = False) -> MultiTenancyConfigCreate:
        return MultiTenancyConfigCreate(enabled=enabled)

    @classmethod
    def update(cls, enabled: bool = False) -> MultiTenancyConfigUpdate:
        return MultiTenancyConfigUpdate(enabled=enabled)


class GenerativeConfig(ConfigCreateModel):
    generative: GenerativeSearches


class VectorizerConfig(ConfigCreateModel):
    vectorizer: Vectorizer


class PropertyVectorizerConfigCreate(ConfigCreateModel):
    skip: bool
    vectorizePropertyName: bool


class PropertyVectorizerConfig:
    """This class has no `.update()` method because you cannot update the property vectorizer configuration of Weaviate dynamically"""

    @classmethod
    def create(
        cls, skip: bool = False, vectorize_property_name: bool = True
    ) -> PropertyVectorizerConfigCreate:
        return PropertyVectorizerConfigCreate(
            skip=skip, vectorizePropertyName=vectorize_property_name
        )


class GenerativeFactory:
    @classmethod
    def OpenAI(cls) -> GenerativeConfig:
        """Return a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`"""
        return GenerativeConfig(generative=GenerativeSearches.OPENAI)


class Text2VecContextionaryConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_CONTEXTIONARY, frozen=True, exclude=True
    )
    vectorizeClassName: bool = Field(default=True, alias="vectorize_class_name")


class Text2VecCohereConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_COHERE, frozen=True, exclude=True)
    model: Literal[
        "embed-multilingual-v2.0",
        "small",
        "medium",
        "large",
        "multilingual-22-12",
        "embed-english-v2.0",
        "embed-english-light-v2.0",
    ] = Field(default="embed-multilingual-v2.0")
    truncate: Literal["RIGHT", "NONE"] = Field(default="RIGHT")


class Text2VecHuggingFaceConfigOptions(ConfigCreateModel):
    waitForModel: Optional[bool] = Field(None, alias="wait_for_model")
    useGPU: Optional[bool] = Field(default=None, alias="use_gpu")
    useCache: Optional[bool] = Field(default=None, alias="use_cache")


class Text2VecHuggingFaceConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_HUGGINGFACE, frozen=True, exclude=True
    )
    model: Optional[str] = Field(default=None)
    passageModel: Optional[str] = Field(default=None, alias="passage_model")
    queryModel: Optional[str] = Field(default=None, alias="query_model")
    endpointURL: Optional[str] = Field(default=None, alias="endpoint_url")
    options: Optional[Text2VecHuggingFaceConfigOptions] = Field(default=None)

    @model_validator(mode="before")
    def validate_mutually_exclusive_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "passageModel" in values and "queryModel" not in values:
            raise ValueError("Must specify queryModel when specifying passageModel")
        if "queryModel" in values and "passageModel" not in values:
            raise ValueError("Must specify passageModel when specifying queryModel")
        if "model" in values and any(["passageModel" in values, "queryModel" in values]):
            raise ValueError("Can only specify model alone or passageModel and queryModel together")
        if (
            any(["passageModel" in values, "queryModel" in values, "model" in values])
            and "endpointURL" in values
        ):
            _Warnings.text2vec_huggingface_endpoint_url_and_model_set_together()
        return values


class Text2VecOpenAIConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_OPENAI, frozen=True, exclude=True)
    model: Optional[Literal["ada", "babbage", "curie", "davinci"]] = None
    modelVersion: Optional[str] = Field(default=None, alias="model_version")
    type_: Optional[Literal["text", "code"]] = None
    vectorizeClassName: bool = Field(default=True, alias="vectorize_class_name")

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        try:
            ret_dict["type"] = ret_dict.pop("type_")
        except KeyError:
            pass
        return ret_dict


class Text2VecAzureOpenAIConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_OPENAI, frozen=True, exclude=True)
    resourceName: str = Field(default=..., alias="resource_name")
    deploymentId: str = Field(default=..., alias="deployment_id")


class Text2VecPalmConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_PALM, frozen=True, exclude=True)
    projectId: str = Field(default=..., alias="project_id")
    apiEndpoint: Optional[str] = Field(default=None, alias="api_endpoint")
    modelId: Optional[str] = Field(default=None, alias="model_id")
    vectorizeClassName: bool = Field(default=True, alias="vectorize_class_name")


class Text2VecTransformersConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_TRANSFORMERS, frozen=True, exclude=True
    )
    poolingStrategy: Literal["masked_mean", "cls"] = Field(
        default="masked_mean", alias="pooling_strategy"
    )
    vectorizeClassName: bool = Field(default=True, alias="vectorize_class_name")


class Text2VecGPT4AllConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_GPT4ALL, frozen=True, exclude=True)
    vectorizeClassName: bool = Field(default=True, alias="vectorize_class_name")


class Img2VecNeuralConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.IMG2VEC_NEURAL, frozen=True, exclude=True)
    imageFields: List[str] = Field(default=..., alias="image_fields")


class Multi2VecClipConfigWeights(ConfigCreateModel):
    imageFields: Optional[List[float]] = Field(None, alias="image_fields")
    textFields: Optional[List[float]] = Field(None, alias="text_fields")


class Multi2VecClipConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(Vectorizer.MULTI2VEC_CLIP, frozen=True, exclude=True)
    imageFields: Optional[List[str]] = Field(None, alias="image_fields")
    textFields: Optional[List[str]] = Field(None, alias="text_fields")
    vectorizeClassName: bool = Field(True, alias="vectorize_class_name")
    weights: Optional[Multi2VecClipConfigWeights] = None


class Multi2VecBindConfigWeights(ConfigCreateModel):
    audioFields: Optional[List[float]] = Field(None, alias="audio_fields")
    depthFields: Optional[List[float]] = Field(None, alias="depth_fields")
    imageFields: Optional[List[float]] = Field(None, alias="image_fields")
    IMUFields: Optional[List[float]] = Field(None, alias="imu_fields")
    textFields: Optional[List[float]] = Field(None, alias="text_fields")
    thermalFields: Optional[List[float]] = Field(None, alias="thermal_fields")
    videoFields: Optional[List[float]] = Field(None, alias="video_fields")


class Multi2VecBindConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(Vectorizer.MULTI2VEC_BIND, frozen=True, exclude=True)
    audioFields: Optional[List[str]] = Field(None, alias="audio_fields")
    depthFields: Optional[List[str]] = Field(None, alias="depth_fields")
    imageFields: Optional[List[str]] = Field(None, alias="image_fields")
    IMUFields: Optional[List[str]] = Field(None, alias="imu_fields")
    textFields: Optional[List[str]] = Field(None, alias="text_fields")
    thermalFields: Optional[List[str]] = Field(None, alias="thermal_fields")
    videoFields: Optional[List[str]] = Field(None, alias="video_fields")
    vectorizeClassName: bool = Field(True, alias="vectorize_class_name")
    weights: Optional[Multi2VecBindConfigWeights] = None


class Ref2VecCentroidConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(Vectorizer.REF2VEC_CENTROID, frozen=True, exclude=True)
    referenceProperties: List[str] = Field(..., alias="reference_properties")
    method: Literal["mean"] = "mean"


class VectorizerFactory:
    @classmethod
    def none(cls) -> VectorizerConfig:
        """Return a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`"""
        return VectorizerConfig(vectorizer=Vectorizer.NONE)

    @classmethod
    def auto(cls) -> None:
        """Returns a `VectorizerConfig` object with the `Vectorizer` auto-detected from the environment
        variables of the client or Weaviate itself"""
        # TODO: Can this be done?
        pass

    @classmethod
    def text2vec_contextionary(
        cls, vectorize_class_name: bool = True
    ) -> "Text2VecContextionaryConfig":
        """Returns a `Text2VecContextionaryConfig` object for use when vectorizing using the text2vec-contextionary model"""
        return Text2VecContextionaryConfig(vectorize_class_name=vectorize_class_name)


class CollectionConfigCreateBase(ConfigCreateModel):
    description: Optional[str] = Field(default=None)
    invertedIndexConfig: Optional[InvertedIndexConfigCreate] = Field(
        default=None, alias="inverted_index_config"
    )
    multiTenancyConfig: Optional[MultiTenancyConfigCreate] = Field(
        default=None, alias="multi_tenancy_config"
    )
    replicationConfig: Optional[ReplicationConfigCreate] = Field(
        default=None, alias="replication_config"
    )
    shardingConfig: Optional[ShardingConfigCreate] = Field(default=None, alias="sharding_config")
    vectorIndexConfig: Optional[VectorIndexConfigCreate] = Field(
        default=None, alias="vector_index_config"
    )
    vectorIndexType: VectorIndexType = Field(
        default=VectorIndexType.HNSW, alias="vector_index_type"
    )
    moduleConfig: VectorizerConfig = Field(
        default=VectorizerFactory.none(), alias="vectorizer_config"
    )
    generativeSearch: Optional[GenerativeConfig] = Field(default=None, alias="generative_search")

    def to_dict(self) -> Dict[str, Any]:
        ret_dict: Dict[str, Any] = {}

        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if cls_field in ["name", "model", "properties"] or val is None:
                continue
            if isinstance(val, Enum):
                ret_dict[cls_field] = str(val.value)
            elif isinstance(val, (bool, float, str, int)):
                ret_dict[cls_field] = str(val)
            elif isinstance(val, GenerativeConfig):
                self.__add_to_module_config(ret_dict, val.generative.value, {})
            elif isinstance(val, VectorizerConfig):
                ret_dict["vectorizer"] = val.vectorizer.value
                if val.vectorizer != Vectorizer.NONE:
                    self.__add_to_module_config(ret_dict, val.vectorizer.value, val.to_dict())
            else:
                assert isinstance(val, ConfigCreateModel)
                ret_dict[cls_field] = val.to_dict()
        if self.moduleConfig is None:
            ret_dict["vectorizer"] = Vectorizer.NONE.value
        return ret_dict

    @staticmethod
    def __add_to_module_config(
        return_dict: Dict[str, Any], addition_key: str, addition_val: Dict[str, Any]
    ) -> None:
        if "moduleConfig" not in return_dict:
            return_dict["moduleConfig"] = {addition_key: addition_val}
        else:
            return_dict["moduleConfig"][addition_key] = addition_val


class CollectionConfigUpdate(ConfigUpdateModel):
    description: Optional[str] = Field(default=None)
    invertedIndexConfig: Optional[InvertedIndexConfigUpdate] = Field(
        default=None, alias="inverted_index_config"
    )
    replicationConfig: Optional[ReplicationConfigUpdate] = Field(
        default=None, alias="replication_config"
    )
    vectorIndexConfig: Optional[VectorIndexConfigUpdate] = Field(
        default=None, alias="vector_index_config"
    )


@dataclass
class _BM25Config:
    b: float
    k1: float


@dataclass
class _StopwordsConfig:
    preset: StopwordsPreset
    additions: Optional[List[str]]
    removals: Optional[List[str]]


@dataclass
class _InvertedIndexConfig:
    bm25: _BM25Config
    cleanup_interval_seconds: int
    stopwords: _StopwordsConfig


@dataclass
class _MultiTenancyConfig:
    enabled: bool


@dataclass
class _ReferenceDataType:
    target_collection: str


@dataclass
class _ReferenceDataTypeMultiTarget:
    target_collections: List[str]


@dataclass
class _Property:
    data_type: Union[DataType, _ReferenceDataType, _ReferenceDataTypeMultiTarget]
    description: Optional[str]
    index_filterable: bool
    index_searchable: bool
    name: str
    tokenization: Optional[Tokenization]

    def to_weaviate_dict(self) -> Dict[str, Any]:
        if isinstance(self.data_type, DataType):
            data_type = [self.data_type.value]
        elif isinstance(self.data_type, _ReferenceDataType):
            data_type = [self.data_type.target_collection]
        else:
            data_type = self.data_type.target_collections
        return {
            "dataType": data_type,
            "description": self.description,
            "indexFilterable": self.index_filterable,
            "indexVector": self.index_searchable,
            "name": self.name,
            "tokenizer": self.tokenization.value if self.tokenization else None,
        }


@dataclass
class _ReplicationFactor:
    factor: int


@dataclass
class _ShardingConfig:
    virtual_per_physical: int
    desired_count: int
    actual_count: int
    desired_virtual_count: int
    actual_virtual_count: int
    key: str
    strategy: str
    function: str


@dataclass
class _PQEncoderConfig:
    type_: PQEncoderType
    distribution: PQEncoderDistribution


@dataclass
class _PQConfig:
    enabled: bool
    bit_compression: bool
    segments: int
    centroids: int
    training_limit: int
    encoder: _PQEncoderConfig


@dataclass
class _VectorIndexConfig:
    cleanup_interval_seconds: int
    distance: VectorDistance
    dynamic_ef_min: int
    dynamic_ef_max: int
    dynamic_ef_factor: int
    ef: int
    ef_construction: int
    flat_search_cutoff: int
    max_connections: int
    pq: _PQConfig
    skip: bool
    vector_cache_max_objects: int


@dataclass
class _CollectionConfig:
    name: str
    description: Optional[str]
    inverted_index_config: _InvertedIndexConfig
    multi_tenancy_config: _MultiTenancyConfig
    properties: List[_Property]
    replication_factor: _ReplicationFactor
    sharding_config: _ShardingConfig
    vector_index_config: _VectorIndexConfig
    vector_index_type: VectorIndexType
    vectorizer: Vectorizer


# class PropertyConfig(ConfigCreateModel):
#     indexFilterable: Optional[bool] = Field(None, alias="index_filterable")
#     indexSearchable: Optional[bool] = Field(None, alias="index_searchable")
#     tokenization: Optional[Tokenization] = None
#     description: Optional[str] = None
#     moduleConfig: Optional[ModuleConfig] = Field(None, alias="module_config")


@dataclass
class PropertyConfig:
    index_filterable: Optional[bool] = None
    index_searchable: Optional[bool] = None
    tokenization: Optional[Tokenization] = None
    description: Optional[str] = None
    vectorizer_config: Optional[VectorizerConfig] = None

    # tmp solution. replace with a pydantic BaseModel, see bugreport: https://github.com/pydantic/pydantic/issues/6948
    # bugreport was closed as not planned :( so dataclasses must stay
    def to_dict(self) -> Dict[str, Any]:
        return {
            "indexFilterable": self.index_filterable,
            "indexSearchable": self.index_searchable,
            "tokenization": self.tokenization,
            "description": self.description,
            "moduleConfig": self.vectorizer_config,
        }


class Property(ConfigCreateModel):
    name: str
    dataType: DataType = Field(default=..., alias="data_type")
    indexFilterable: Optional[bool] = Field(default=None, alias="index_filterable")
    indexSearchable: Optional[bool] = Field(default=None, alias="index_searchable")
    description: Optional[str] = Field(default=None)
    moduleConfig: Optional[PropertyVectorizerConfigCreate] = Field(
        default=None, alias="vectorizer_config"
    )
    tokenization: Optional[Tokenization] = Field(default=None)

    def to_dict(self, vectorizer: Optional[Vectorizer] = None) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        if "moduleConfig" in ret_dict and vectorizer is not None:
            ret_dict["moduleConfig"] = {vectorizer.value: ret_dict["moduleConfig"]}
        return ret_dict


class ReferencePropertyBase(ConfigCreateModel):
    name: str


class ReferenceProperty(ReferencePropertyBase):
    target_collection: str

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [_capitalize_first_letter(self.target_collection)]
        del ret_dict["target_collection"]
        return ret_dict


class ReferencePropertyMultiTarget(ReferencePropertyBase):
    target_collections: List[str]

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [
            _capitalize_first_letter(target) for target in self.target_collections
        ]
        del ret_dict["target_collections"]
        return ret_dict


PropertyType = Union[Property, ReferenceProperty, ReferencePropertyMultiTarget]


class CollectionConfig(CollectionConfigCreateBase):
    name: str
    properties: Optional[List[Union[Property, ReferencePropertyBase]]] = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        self.name = _capitalize_first_letter(self.name)

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()

        ret_dict["class"] = self.name

        if self.properties is not None:
            ret_dict["properties"] = [
                prop.to_dict(self.moduleConfig.vectorizer)
                if isinstance(prop, Property)
                else prop.to_dict()
                for prop in self.properties
            ]

        return ret_dict

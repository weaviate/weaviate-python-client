from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from weaviate.warnings import _Warnings
from weaviate.util import _capitalize_first_letter


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
        return self.model_dump(exclude_none=True)


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
    type_: PQEncoderType = PQEncoderType.KMEANS
    distribution: PQEncoderDistribution = PQEncoderDistribution.LOG_NORMAL

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Must be done manually since Pydantic does not work well with type and type_.
        Errors shadowing type occur if we want to use type as a field name.
        """
        if self.type_ is not None:
            schema["type"] = str(self.type_.value)
        if self.distribution is not None:
            schema["distribution"] = str(self.distribution.value)
        return schema


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
    bitCompression: bool = Field(default=False, alias="bit_compression")
    centroids: int = 256
    enabled: bool = False
    segments: int = 0
    trainingLimit: int = Field(default=10000, alias="training_limit")
    encoder: PQEncoderConfigCreate = PQEncoderConfigCreate()


class PQConfigUpdate(ConfigUpdateModel):
    bitCompression: Optional[bool] = Field(default=None, alias="bit_compression")
    centroids: Optional[int] = None
    enabled: Optional[bool] = None
    segments: Optional[int] = None
    trainingLimit: Optional[int] = Field(default=None, alias="training_limit")
    encoder: Optional[PQEncoderConfigUpdate] = None


class VectorIndexConfigCreate(ConfigCreateModel):
    cleanupIntervalSeconds: int = Field(default=300, alias="cleanup_interval_seconds")
    distance: VectorDistance = VectorDistance.COSINE
    dynamicEfMin: int = Field(default=100, alias="dynamic_ef_min")
    dynamicEfMax: int = Field(default=500, alias="dynamic_ef_max")
    dynamicEfFactor: int = Field(default=8, alias="dynamic_ef_factor")
    efConstruction: int = Field(default=128, alias="ef_construction")
    ef: int = -1
    flatSearchCutoff: int = Field(default=40000, alias="flat_search_cutoff")
    maxConnections: int = Field(default=64, alias="max_connections")
    pq: PQConfigCreate = PQConfigCreate(bit_compression=False, training_limit=10000)
    skip: bool = False
    vectorCacheMaxObjects: int = Field(default=1000000000000, alias="vector_cache_max_objects")


class VectorIndexConfigUpdate(ConfigUpdateModel):
    dynamicEfFactor: Optional[int] = Field(default=None, alias="dynamic_ef_factor")
    dynamicEfMin: Optional[int] = Field(default=None, alias="dynamic_ef_min")
    dynamicEfMax: Optional[int] = Field(default=None, alias="dynamic_ef_max")
    ef: Optional[int] = None
    flatSearchCutoff: Optional[int] = Field(default=None, alias="flat_search_cutoff")
    skip: Optional[bool] = None
    vectorCacheMaxObjects: Optional[int] = Field(default=None, alias="vector_cache_max_objects")
    pq: Optional[PQConfigUpdate] = None


class ShardingConfigCreate(ConfigCreateModel):
    virtualPerPhysical: int = Field(default=128, alias="virtual_per_physical")
    desiredCount: int = Field(default=1, alias="desired_count")
    actualCount: int = Field(default=1, alias="actual_count")
    desiredVirtualCount: int = Field(default=128, alias="desired_virtual_count")
    actualVirtualCount: int = Field(default=128, alias="actual_virtual_count")
    key: str = "_id"
    strategy: str = "hash"
    function: str = "murmur3"


class ReplicationConfigCreate(ConfigCreateModel):
    factor: int = 1


class ReplicationConfigUpdate(ConfigUpdateModel):
    factor: Optional[int] = None


class BM25ConfigCreate(ConfigCreateModel):
    b: float = 0.75
    k1: float = 1.2


class BM25ConfigUpdate(ConfigUpdateModel):
    b: Optional[float] = None
    k1: Optional[float] = None


class StopwordsCreate(ConfigCreateModel):
    preset: StopwordsPreset = Field(default=StopwordsPreset.EN)
    additions: Optional[List[str]] = Field(default=None)
    removals: Optional[List[str]] = Field(default=None)


class StopwordsUpdate(ConfigUpdateModel):
    preset: Optional[StopwordsPreset] = Field(default=None)
    additions: Optional[List[str]] = None
    removals: Optional[List[str]] = None


class InvertedIndexConfigCreate(ConfigCreateModel):
    bm25: BM25ConfigCreate = BM25ConfigCreate()
    cleanupIntervalSeconds: int = Field(default=60, alias="cleanup_interval_seconds")
    indexTimestamps: bool = Field(default=False, alias="index_timestamps")
    indexPropertyLength: bool = Field(default=False, alias="index_property_length")
    indexNullState: bool = Field(default=False, alias="index_null_state")
    stopwords: StopwordsCreate = StopwordsCreate()


class InvertedIndexConfigUpdate(ConfigUpdateModel):
    bm25: Optional[BM25ConfigUpdate] = Field(default=None)
    cleanupIntervalSeconds: Optional[int] = Field(default=None, alias="cleanup_interval_seconds")
    indexTimestamps: Optional[bool] = Field(default=None, alias="index_timestamps")
    indexPropertyLength: Optional[bool] = Field(default=None, alias="index_property_length")
    indexNullState: Optional[bool] = Field(default=None, alias="index_null_state")
    stopwords: Optional[StopwordsUpdate] = Field(default=None)


class MultiTenancyConfig(ConfigCreateModel):
    enabled: bool = False


class VectorizerConfig(ConfigCreateModel):
    vectorizer: Vectorizer


class PropertyVectorizerConfig(ConfigCreateModel):
    skip: bool = False
    vectorizePropertyName: bool = Field(default=True, alias="vectorize_property_name")


class Text2VecContextionaryConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_CONTEXTIONARY, frozen=True, exclude=True
    )
    vectorizeClassName: bool = Field(default=True, alias="vectorize_class_name")


class Text2VecCohereConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_COHERE, frozen=True, exclude=True)
    model: Literal["embed_multilingual_v2.0"] = Field(default="embed_multilingual_v2.0")
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
    imageFields: Optional[List[float]] = Field(None, alias="image_fields", ge=0, le=1)
    textFields: Optional[List[float]] = Field(None, alias="text_fields", ge=0, le=1)


class Multi2VecClipConfig(VectorizerConfig):
    vectorizer: Vectorizer = Field(Vectorizer.MULTI2VEC_CLIP, frozen=True, exclude=True)
    imageFields: Optional[List[str]] = Field(None, alias="image_fields")
    textFields: Optional[List[str]] = Field(None, alias="text_fields")
    vectorizeClassName: bool = Field(True, alias="vectorize_class_name")
    weights: Optional[Multi2VecClipConfigWeights] = None


class Multi2VecBindConfigWeights(ConfigCreateModel):
    audioFields: Optional[List[float]] = Field(None, alias="audio_fields", ge=0, le=1)
    depthFields: Optional[List[float]] = Field(None, alias="depth_fields", ge=0, le=1)
    imageFields: Optional[List[float]] = Field(None, alias="image_fields", ge=0, le=1)
    IMUFields: Optional[List[float]] = Field(None, alias="imu_fields", ge=0, le=1)
    textFields: Optional[List[float]] = Field(None, alias="text_fields", ge=0, le=1)
    thermalFields: Optional[List[float]] = Field(None, alias="thermal_fields", ge=0, le=1)
    videoFields: Optional[List[float]] = Field(None, alias="video_fields", ge=0, le=1)


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
    description: Optional[str] = None
    invertedIndexConfig: Optional[InvertedIndexConfigCreate] = Field(
        None, alias="inverted_index_config"
    )
    multiTenancyConfig: Optional[MultiTenancyConfig] = Field(None, alias="multi_tenancy_config")
    replicationConfig: Optional[ReplicationConfigCreate] = Field(None, alias="replication_config")
    shardingConfig: Optional[ShardingConfigCreate] = Field(None, alias="sharding_config")
    vectorIndexConfig: Optional[VectorIndexConfigCreate] = Field(None, alias="vector_index_config")
    vectorIndexType: VectorIndexType = Field(VectorIndexType.HNSW, alias="vector_index_type")
    moduleConfig: VectorizerConfig = Field(
        default=VectorizerFactory.none(), alias="vectorizer_config"
    )

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
            elif isinstance(val, VectorizerConfig):
                ret_dict["vectorizer"] = val.vectorizer.value
                if val.vectorizer != Vectorizer.NONE:
                    ret_dict["moduleConfig"] = {val.vectorizer.value: val.to_dict()}
            else:
                assert isinstance(val, ConfigCreateModel)
                ret_dict[cls_field] = val.to_dict()
        if self.moduleConfig is None:
            ret_dict["vectorizer"] = Vectorizer.NONE.value
        return ret_dict


class CollectionConfigUpdate(ConfigUpdateModel):
    description: Optional[str] = None
    invertedIndexConfig: Optional[InvertedIndexConfigUpdate] = Field(
        None, alias="inverted_index_config"
    )
    replicationConfig: Optional[ReplicationConfigUpdate] = Field(None, alias="replication_config")
    vectorIndexConfig: Optional[VectorIndexConfigUpdate] = Field(None, alias="vector_index_config")


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
    dataType: DataType = Field(..., alias="data_type")
    indexFilterable: Optional[bool] = Field(None, alias="index_filterable")
    indexSearchable: Optional[bool] = Field(None, alias="index_searchable")
    description: Optional[str] = Field(None)
    moduleConfig: Optional[PropertyVectorizerConfig] = Field(None, alias="vectorizer_config")
    tokenization: Optional[Tokenization] = Field(None)

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
    """Use this class when specifying all the configuration options relevant to your collection when using
    the non-ORM collections API. This class is a superset of the `CollectionConfigCreateBase` class, and
    includes all the options available to the `CollectionConfigCreateBase` class.

    When using this non-ORM API, you must specify the name and properties of the collection explicitly here.

    Example:
        ```python
        from weaviate.weaviate_classes as wvc

        config = wvc.CollectionConfig(
            name = "MyCollection",
            properties = [
                wvc.Property(
                    name="myProperty",
                    data_type=wvc.DataType.STRING,
                    index_searchable=True,
                    index_filterable=True,
                    description="A string property"
                )
            ]
        )
        ```
    """

    name: str
    properties: Optional[List[Union[Property, ReferencePropertyBase]]] = Field(None)

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

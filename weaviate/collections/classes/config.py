from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import TypeAlias

from pydantic import AnyHttpUrl, Field, field_validator

from weaviate.util import _capitalize_first_letter
from weaviate.collections.classes.config_vectorizers import (
    _Vectorizer,
    _VectorizerConfigCreate,
    CohereModel,
    Vectorizers as VectorizersAlias,
    VectorDistances as VectorDistancesAlias,
)

from weaviate.collections.classes.config_base import (
    _ConfigBase,
    _ConfigCreateModel,
    _ConfigUpdateModel,
    _QuantizerConfigUpdate,
)

from weaviate.collections.classes.config_vector_index import (
    _QuantizerConfigCreate,
    _VectorIndexConfigCreate,
    _VectorIndexConfigHNSWCreate,
    _VectorIndexConfigFlatCreate,
    _VectorIndexConfigHNSWUpdate,
    _VectorIndexConfigFlatUpdate,
    _VectorIndexConfigSkipCreate,
    _VectorIndexConfigUpdate,
    VectorIndexType as VectorIndexTypeAlias,
)

from weaviate.collections.classes.config_named_vectors import (
    _NamedVectorConfigCreate,
    _NamedVectorConfigUpdate,
    _NamedVectors,
    _NamedVectorsUpdate,
)
from weaviate.exceptions import WeaviateInvalidInputError

# BC for direct imports
Vectorizers: TypeAlias = VectorizersAlias
VectorIndexType: TypeAlias = VectorIndexTypeAlias
VectorDistances: TypeAlias = VectorDistancesAlias


class ConsistencyLevel(str, Enum):
    """The consistency levels when writing to Weaviate with replication enabled.

    Attributes:
        ALL: Wait for confirmation of write success from all, `N`, replicas.
        ONE: Wait for confirmation of write success from only one replica.
        QUORUM: Wait for confirmation of write success from a quorum: `N/2+1`, of replicas.
    """

    ALL = "ALL"
    ONE = "ONE"
    QUORUM = "QUORUM"


class DataType(str, Enum):
    """The available primitive data types in Weaviate.

    Attributes:
        TEXT: Text data type.
        TEXT_ARRAY: Text array data type.
        INT: Integer data type.
        INT_ARRAY: Integer array data type.
        BOOL: Boolean data type.
        BOOL_ARRAY: Boolean array data type.
        NUMBER: Number data type.
        NUMBER_ARRAY: Number array data type.
        DATE: Date data type.
        DATE_ARRAY: Date array data type.
        UUID: UUID data type.
        UUID_ARRAY: UUID array data type.
        GEO_COORDINATES: Geo coordinates data type.
        BLOB: Blob data type.
        PHONE_NUMBER: Phone number data type.
        OBJECT: Object data type.
        OBJECT_ARRAY: Object array data type.
    """

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
    OBJECT = "object"
    OBJECT_ARRAY = "object[]"


class Tokenization(str, Enum):
    """The available inverted index tokenization methods for text properties in Weaviate.

    Attributes:
        `WORD`
            Tokenize by word.
        `WHITESPACE`
            Tokenize by whitespace.
        `LOWERCASE`
            Tokenize by lowercase.
        `FIELD`
            Tokenize by field.
        `GSE`
            Tokenize using GSE (for Chinese and Japanese).
        `TRIGRAM`
            Tokenize into trigrams.
    """

    WORD = "word"
    WHITESPACE = "whitespace"
    LOWERCASE = "lowercase"
    FIELD = "field"
    GSE = "gse"
    TRIGRAM = "trigram"


class GenerativeSearches(str, Enum):
    """The available generative search modules in Weaviate.

    These modules generate text from text-based inputs.
    See the [docs](https://weaviate.io/developers/weaviate/modules/reader-generator-modules) for more details.

    Attributes:
        `OPENAI`
            Weaviate module backed by OpenAI and Azure-OpenAI generative models.
        `COHERE`
            Weaviate module backed by Cohere generative models.
        `PALM`
            Weaviate module backed by PaLM generative models.
        `AWS`
            Weaviate module backed by AWS Bedrock generative models.
    """

    OPENAI = "generative-openai"
    COHERE = "generative-cohere"
    PALM = "generative-palm"
    AWS = "generative-aws"
    ANYSCALE = "generative-anyscale"


class Rerankers(str, Enum):
    """The available reranker modules in Weaviate.

    These modules rerank the results of a search query.
    See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules#re-ranking) for more details.

    Attributes:
        `NONE`
            No reranker.
        `COHERE`
            Weaviate module backed by Cohere reranking models.
        `TRANSFORMERS`
            Weaviate module backed by Transformers reranking models.
    """

    NONE = "none"
    COHERE = "reranker-cohere"
    TRANSFORMERS = "reranker-transformers"


class StopwordsPreset(str, Enum):
    """Preset stopwords to use in the `Stopwords` class.

    Attributes:
        `EN`
            English stopwords.
        `NONE`
            No stopwords.
    """

    NONE = "none"
    EN = "en"


class PQEncoderType(str, Enum):
    """Type of the PQ encoder.

    Attributes:
        `KMEANS`
            K-means encoder.
        `TILE`
            Tile encoder.
    """

    KMEANS = "kmeans"
    TILE = "tile"


class PQEncoderDistribution(str, Enum):
    """Distribution of the PQ encoder.

    Attributes:
        `LOG_NORMAL`
            Log-normal distribution.
        `NORMAL`
            Normal distribution.
    """

    LOG_NORMAL = "log-normal"
    NORMAL = "normal"


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
    bitCompression: Optional[bool]
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


class _PQConfigUpdate(_QuantizerConfigUpdate):
    bitCompression: Optional[bool]
    centroids: Optional[int]
    enabled: Optional[bool]
    segments: Optional[int]
    trainingLimit: Optional[int]
    encoder: Optional[_PQEncoderConfigUpdate]

    @staticmethod
    def quantizer_name() -> str:
        return "pq"


class _BQConfigUpdate(_QuantizerConfigUpdate):
    rescoreLimit: Optional[int]

    @staticmethod
    def quantizer_name() -> str:
        return "bq"


class _ShardingConfigCreate(_ConfigCreateModel):
    virtualPerPhysical: Optional[int]
    desiredCount: Optional[int]
    actualCount: Optional[int]
    desiredVirtualCount: Optional[int]
    actualVirtualCount: Optional[int]
    key: str = "_id"
    strategy: str = "hash"
    function: str = "murmur3"


class _ReplicationConfigCreate(_ConfigCreateModel):
    factor: Optional[int]


class _ReplicationConfigUpdate(_ConfigUpdateModel):
    factor: Optional[int]


class _BM25ConfigCreate(_ConfigCreateModel):
    b: float
    k1: float


class _BM25ConfigUpdate(_ConfigUpdateModel):
    b: Optional[float]
    k1: Optional[float]


class _StopwordsCreate(_ConfigCreateModel):
    preset: Optional[StopwordsPreset]
    additions: Optional[List[str]]
    removals: Optional[List[str]]


class _StopwordsUpdate(_ConfigUpdateModel):
    preset: Optional[StopwordsPreset]
    additions: Optional[List[str]]
    removals: Optional[List[str]]


class _InvertedIndexConfigCreate(_ConfigCreateModel):
    bm25: Optional[_BM25ConfigCreate]
    cleanupIntervalSeconds: Optional[int]
    indexTimestamps: Optional[bool]
    indexPropertyLength: Optional[bool]
    indexNullState: Optional[bool]
    stopwords: _StopwordsCreate


class _InvertedIndexConfigUpdate(_ConfigUpdateModel):
    bm25: Optional[_BM25ConfigUpdate]
    cleanupIntervalSeconds: Optional[int]
    stopwords: Optional[_StopwordsUpdate]


class _MultiTenancyConfigCreate(_ConfigCreateModel):
    enabled: bool


class _MultiTenancyConfigUpdate(_ConfigUpdateModel):
    enabled: Optional[bool] = None


class _GenerativeConfigCreate(_ConfigCreateModel):
    generative: GenerativeSearches


class _GenerativeAnyscale(_GenerativeConfigCreate):
    generative: GenerativeSearches = Field(
        default=GenerativeSearches.ANYSCALE, frozen=True, exclude=True
    )
    temperature: Optional[float]
    model: Optional[str]


class _GenerativeOpenAIConfigBase(_GenerativeConfigCreate):
    generative: GenerativeSearches = Field(
        default=GenerativeSearches.OPENAI, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    frequencyPenaltyProperty: Optional[float]
    presencePenaltyProperty: Optional[float]
    maxTokensProperty: Optional[int]
    temperatureProperty: Optional[float]
    topPProperty: Optional[float]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _GenerativeOpenAIConfig(_GenerativeOpenAIConfigBase):
    model: Optional[str]


class _GenerativeAzureOpenAIConfig(_GenerativeOpenAIConfigBase):
    resourceName: str
    deploymentId: str


class _GenerativeCohereConfig(_GenerativeConfigCreate):
    generative: GenerativeSearches = Field(
        default=GenerativeSearches.COHERE, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    kProperty: Optional[int]
    model: Optional[str]
    maxTokensProperty: Optional[int]
    returnLikelihoodsProperty: Optional[str]
    stopSequencesProperty: Optional[List[str]]
    temperatureProperty: Optional[float]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _GenerativePaLMConfig(_GenerativeConfigCreate):
    generative: GenerativeSearches = Field(
        default=GenerativeSearches.PALM, frozen=True, exclude=True
    )
    apiEndpoint: Optional[str]
    maxOutputTokens: Optional[int]
    modelId: Optional[str]
    projectId: str
    temperature: Optional[float]
    topK: Optional[int]
    topP: Optional[float]


class _GenerativeAWSConfig(_GenerativeConfigCreate):
    generative: GenerativeSearches = Field(
        default=GenerativeSearches.AWS, frozen=True, exclude=True
    )
    model: str
    region: str


class _RerankerConfigCreate(_ConfigCreateModel):
    reranker: Rerankers


RerankerCohereModel = Literal["rerank-english-v2.0", "rerank-multilingual-v2.0"]


class _RerankerCohereConfig(_RerankerConfigCreate):
    reranker: Rerankers = Field(default=Rerankers.COHERE, frozen=True, exclude=True)
    model: Optional[Union[RerankerCohereModel, str]] = Field(default=None)


class _RerankerTransformersConfig(_RerankerConfigCreate):
    reranker: Rerankers = Field(default=Rerankers.TRANSFORMERS, frozen=True, exclude=True)


class _Generative:
    """Use this factory class to create the correct object for the `generative_config` argument in the `collections.create()` method.

    Each staticmethod provides options specific to the named generative search module in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @staticmethod
    def anyscale(
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> _GenerativeConfigCreate:
        return _GenerativeAnyscale(model=model, temperature=temperature)

    @staticmethod
    def openai(
        model: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _GenerativeConfigCreate:
        """Create a `_GenerativeOpenAIConfig` object for use when performing AI generation using the `generative-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `frequency_penalty`
                The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `presence_penalty`
                The presence penalty to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeOpenAIConfig(
            baseURL=base_url,
            frequencyPenaltyProperty=frequency_penalty,
            maxTokensProperty=max_tokens,
            model=model,
            presencePenaltyProperty=presence_penalty,
            temperatureProperty=temperature,
            topPProperty=top_p,
        )

    @staticmethod
    def azure_openai(
        resource_name: str,
        deployment_id: str,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _GenerativeConfigCreate:
        """Create a `_GenerativeAzureOpenAIConfig` object for use when performing AI generation using the `generative-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai)
        for detailed usage.

        Arguments:
            `resource_name`
                The name of the Azure OpenAI resource to use.
            `deployment_id`
                The Azure OpenAI deployment ID to use.
            `frequency_penalty`
                The frequency penalty to use. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `presence_penalty`
                The presence penalty to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeAzureOpenAIConfig(
            baseURL=base_url,
            deploymentId=deployment_id,
            frequencyPenaltyProperty=frequency_penalty,
            maxTokensProperty=max_tokens,
            presencePenaltyProperty=presence_penalty,
            resourceName=resource_name,
            temperatureProperty=temperature,
            topPProperty=top_p,
        )

    @staticmethod
    def cohere(
        model: Optional[Union[CohereModel, str]] = None,
        k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        return_likelihoods: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _GenerativeConfigCreate:
        """Create a `_GenerativeCohereConfig` object for use when performing AI generation using the `generative-cohere` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-cohere)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
            `k`
                The number of sequences to generate. Defaults to `None`, which uses the server-defined default
            `max_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `return_likelihoods`
                Whether to return the likelihoods. Defaults to `None`, which uses the server-defined default
            `stop_sequences`
                The stop sequences to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `base_url`
                The base URL where the API request should go. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativeCohereConfig(
            baseURL=base_url,
            kProperty=k,
            maxTokensProperty=max_tokens,
            model=model,
            returnLikelihoodsProperty=return_likelihoods,
            stopSequencesProperty=stop_sequences,
            temperatureProperty=temperature,
        )

    @staticmethod
    def palm(
        project_id: str,
        api_endpoint: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfigCreate:
        """Create a `_GenerativePaLMConfig` object for use when performing AI generation using the `generative-palm` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-palm)
        for detailed usage.

        Arguments:
            `project_id`
                The PalM project ID to use.
            `api_endpoint`
                The API endpoint to use without a leading scheme such as `http://`. Defaults to `None`, which uses the server-defined default
            `max_output_tokens`
                The maximum number of tokens to generate. Defaults to `None`, which uses the server-defined default
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default
            `temperature`
                The temperature to use. Defaults to `None`, which uses the server-defined default
            `top_k`
                The top K to use. Defaults to `None`, which uses the server-defined default
            `top_p`
                The top P to use. Defaults to `None`, which uses the server-defined default
        """
        return _GenerativePaLMConfig(
            apiEndpoint=api_endpoint,
            maxOutputTokens=max_output_tokens,
            modelId=model_id,
            projectId=project_id,
            temperature=temperature,
            topK=top_k,
            topP=top_p,
        )

    @staticmethod
    def aws(
        model: str,
        region: str,
    ) -> _GenerativeConfigCreate:
        """Create a `_GenerativeAWSConfig` object for use when performing AI generation using the `generative-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-aws)
        for detailed usage.

        Arguments:
            `model`
                The model to use, REQUIRED.
            `region`
                The AWS region to run the model from, REQUIRED.
        """
        return _GenerativeAWSConfig(
            model=model,
            region=region,
        )


class _Reranker:
    """Use this factory class to create the correct object for the `reranker_config` argument in the `collections.create()` method.

    Each staticmethod provides options specific to the named reranker in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @staticmethod
    def transformers() -> _RerankerConfigCreate:
        """Create a `_RerankerTransformersConfig` object for use when reranking using the `reranker-transformers` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/reranker-transformers)
        for detailed usage.
        """
        return _RerankerTransformersConfig(reranker=Rerankers.TRANSFORMERS)

    @staticmethod
    def cohere(
        model: Optional[Union[RerankerCohereModel, str]] = None,
    ) -> _RerankerConfigCreate:
        """Create a `_RerankerCohereConfig` object for use when reranking using the `reranker-cohere` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/reranker-cohere)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default
        """
        return _RerankerCohereConfig(model=model)


class _CollectionConfigCreateBase(_ConfigCreateModel):
    description: Optional[str] = Field(default=None)
    invertedIndexConfig: Optional[_InvertedIndexConfigCreate] = Field(
        default=None, alias="inverted_index_config"
    )
    multiTenancyConfig: Optional[_MultiTenancyConfigCreate] = Field(
        default=None, alias="multi_tenancy_config"
    )
    replicationConfig: Optional[_ReplicationConfigCreate] = Field(
        default=None, alias="replication_config"
    )
    shardingConfig: Optional[_ShardingConfigCreate] = Field(default=None, alias="sharding_config")
    vectorIndexConfig: Optional[_VectorIndexConfigCreate] = Field(
        default=None, alias="vector_index_config"
    )
    moduleConfig: _VectorizerConfigCreate = Field(
        default=_Vectorizer.none(), alias="vectorizer_config"
    )
    generativeSearch: Optional[_GenerativeConfigCreate] = Field(
        default=None, alias="generative_config"
    )
    rerankerConfig: Optional[_RerankerConfigCreate] = Field(default=None, alias="reranker_config")

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict: Dict[str, Any] = {}

        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if cls_field in ["name", "model", "properties", "references"] or val is None:
                continue
            elif isinstance(val, (bool, float, str, int)):
                ret_dict[cls_field] = str(val)
            elif isinstance(val, _GenerativeConfigCreate):
                self.__add_to_module_config(ret_dict, val.generative.value, val._to_dict())
            elif isinstance(val, _RerankerConfigCreate):
                self.__add_to_module_config(ret_dict, val.reranker.value, val._to_dict())
            elif isinstance(val, _VectorizerConfigCreate):
                ret_dict["vectorizer"] = val.vectorizer.value
                if val.vectorizer != Vectorizers.NONE:
                    self.__add_to_module_config(ret_dict, val.vectorizer.value, val._to_dict())
            elif isinstance(val, _VectorIndexConfigCreate):
                ret_dict["vectorIndexType"] = val.vector_index_type()
                ret_dict[cls_field] = val._to_dict()
            else:
                assert isinstance(val, _ConfigCreateModel)
                ret_dict[cls_field] = val._to_dict()
        if self.vectorIndexConfig is None:
            ret_dict["vectorIndexType"] = VectorIndexType.HNSW.value
        return ret_dict

    @staticmethod
    def __add_to_module_config(
        return_dict: Dict[str, Any], addition_key: str, addition_val: Dict[str, Any]
    ) -> None:
        if "moduleConfig" not in return_dict:
            return_dict["moduleConfig"] = {addition_key: addition_val}
        else:
            return_dict["moduleConfig"][addition_key] = addition_val


class _CollectionConfigUpdate(_ConfigUpdateModel):
    description: Optional[str] = Field(default=None)
    invertedIndexConfig: Optional[_InvertedIndexConfigUpdate] = Field(
        default=None, alias="inverted_index_config"
    )
    replicationConfig: Optional[_ReplicationConfigUpdate] = Field(
        default=None, alias="replication_config"
    )
    vectorIndexConfig: Optional[_VectorIndexConfigUpdate] = Field(
        default=None, alias="vector_index_config"
    )
    vectorizerConfig: Optional[
        Union[_VectorIndexConfigUpdate, List[_NamedVectorConfigUpdate]]
    ] = Field(default=None, alias="vectorizer_config")

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        if self.description is not None:
            schema["description"] = self.description
        if self.invertedIndexConfig is not None:
            schema["invertedIndexConfig"] = self.invertedIndexConfig.merge_with_existing(
                schema["invertedIndexConfig"]
            )
        if self.replicationConfig is not None:
            schema["replicationConfig"] = self.replicationConfig.merge_with_existing(
                schema["replicationConfig"]
            )
        if self.vectorIndexConfig is not None:
            schema["vectorIndexConfig"] = self.vectorIndexConfig.merge_with_existing(
                schema["vectorIndexConfig"]
            )
        if self.vectorizerConfig is not None:
            if isinstance(self.vectorizerConfig, _VectorIndexConfigUpdate):
                schema["vectorIndexConfig"] = self.vectorizerConfig.merge_with_existing(
                    schema["vectorIndexConfig"]
                )
            else:
                for vc in self.vectorizerConfig:
                    if vc.name not in schema["vectorConfig"]:
                        raise WeaviateInvalidInputError(
                            f"Vector config with name {vc.name} does not exist in the existing vector config"
                        )
                    if (
                        isinstance(vc.vectorIndexConfig.quantizer, _PQConfigUpdate)
                        and schema["vectorConfig"][vc.name]["vectorIndexConfig"]["bq"]["enabled"]
                        is True
                    ) or (
                        isinstance(vc.vectorIndexConfig.quantizer, _BQConfigUpdate)
                        and schema["vectorConfig"][vc.name]["vectorIndexConfig"]["pq"]["enabled"]
                        is True
                    ):
                        raise WeaviateInvalidInputError(
                            f"Cannot update vector index config with name {vc.name} to change its quantizer"
                        )
                    schema["vectorConfig"][vc.name][
                        "vectorIndexConfig"
                    ] = vc.vectorIndexConfig.merge_with_existing(
                        schema["vectorConfig"][vc.name]["vectorIndexConfig"]
                    )
                    schema["vectorConfig"][vc.name][
                        "vectorIndexType"
                    ] = vc.vectorIndexConfig.vector_index_type()
        return schema


@dataclass
class _BM25Config(_ConfigBase):
    b: float
    k1: float


BM25Config = _BM25Config


@dataclass
class _StopwordsConfig(_ConfigBase):
    preset: StopwordsPreset
    additions: Optional[List[str]]
    removals: Optional[List[str]]


StopwordsConfig = _StopwordsConfig


@dataclass
class _InvertedIndexConfig(_ConfigBase):
    bm25: BM25Config
    cleanup_interval_seconds: int
    index_null_state: bool
    index_property_length: bool
    index_timestamps: bool
    stopwords: StopwordsConfig


InvertedIndexConfig = _InvertedIndexConfig


@dataclass
class _MultiTenancyConfig(_ConfigBase):
    enabled: bool


MultiTenancyConfig = _MultiTenancyConfig


@dataclass
class _PropertyVectorizerConfig:
    skip: bool
    vectorize_property_name: bool


PropertyVectorizerConfig = _PropertyVectorizerConfig


@dataclass
class _NestedProperty:
    data_type: DataType
    description: Optional[str]
    index_filterable: bool
    index_searchable: bool
    name: str
    nested_properties: Optional[List["NestedProperty"]]
    tokenization: Optional[Tokenization]


NestedProperty = _NestedProperty


@dataclass
class _PropertyBase(_ConfigBase):
    name: str
    description: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        out = {"name": self.name}

        if self.description is not None:
            out["description"] = self.description
        return out


@dataclass
class _Property(_PropertyBase):
    data_type: DataType
    index_filterable: bool
    index_searchable: bool
    nested_properties: Optional[List[NestedProperty]]
    tokenization: Optional[Tokenization]
    vectorizer_config: Optional[PropertyVectorizerConfig]
    vectorizer: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        out = super().to_dict()
        out["dataType"] = [self.data_type.value]
        out["indexFilterable"] = self.index_filterable
        out["indexVector"] = self.index_searchable
        out["tokenizer"] = self.tokenization.value if self.tokenization else None

        module_config: Dict[str, Any] = {}
        if self.vectorizer is not None:
            module_config[self.vectorizer] = {}
        if self.vectorizer_config is not None:
            assert self.vectorizer is not None
            module_config[self.vectorizer] = {
                "skip": self.vectorizer_config.skip,
                "vectorizePropertyName": self.vectorizer_config.vectorize_property_name,
            }

        if len(module_config) > 0:
            out["moduleConfig"] = module_config
        return out


PropertyConfig = _Property


@dataclass
class _ReferenceProperty(_PropertyBase):
    target_collections: List[str]

    def to_dict(self) -> Dict[str, Any]:
        out = super().to_dict()
        out["dataType"] = self.target_collections
        return out


ReferencePropertyConfig = _ReferenceProperty


@dataclass
class _ReplicationConfig(_ConfigBase):
    factor: int


ReplicationConfig = _ReplicationConfig


@dataclass
class _ShardingConfig(_ConfigBase):
    virtual_per_physical: int
    desired_count: int
    actual_count: int
    desired_virtual_count: int
    actual_virtual_count: int
    key: str
    strategy: str
    function: str


ShardingConfig = _ShardingConfig


@dataclass
class _PQEncoderConfig(_ConfigBase):
    type_: PQEncoderType
    distribution: PQEncoderDistribution

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["type"] = str(ret_dict.pop("type"))
        ret_dict["distribution"] = str(ret_dict.pop("distribution"))
        return ret_dict


PQEncoderConfig = _PQEncoderConfig


@dataclass
class _PQConfig(_ConfigBase):
    bit_compression: bool
    segments: int
    centroids: int
    training_limit: int
    encoder: PQEncoderConfig


PQConfig = _PQConfig


@dataclass
class _BQConfig(_ConfigBase):
    cache: Optional[bool]
    rescore_limit: int


BQConfig = _BQConfig


@dataclass
class _VectorIndexConfig(_ConfigBase):
    quantizer: Optional[Union[PQConfig, BQConfig]]

    def to_dict(self) -> Dict[str, Any]:
        out = super().to_dict()
        if isinstance(self.quantizer, _PQConfig):
            out["pq"] = {**out.pop("quantizer"), "enabled": True}
        elif isinstance(self.quantizer, _BQConfig):
            out["bq"] = {**out.pop("quantizer"), "enabled": True}
        return out


@dataclass
class _VectorIndexConfigHNSW(_VectorIndexConfig):
    cleanup_interval_seconds: int
    distance_metric: VectorDistances
    dynamic_ef_min: int
    dynamic_ef_max: int
    dynamic_ef_factor: int
    ef: int
    ef_construction: int
    flat_search_cutoff: int
    max_connections: int
    skip: bool
    vector_cache_max_objects: int

    @staticmethod
    def vector_index_type() -> str:
        return VectorIndexType.HNSW.value


VectorIndexConfigHNSW = _VectorIndexConfigHNSW


@dataclass
class _VectorIndexConfigFlat(_VectorIndexConfig):
    distance_metric: VectorDistances
    vector_cache_max_objects: int

    @staticmethod
    def vector_index_type() -> str:
        return VectorIndexType.FLAT.value


VectorIndexConfigFlat = _VectorIndexConfigFlat


@dataclass
class _GenerativeConfig(_ConfigBase):
    generative: GenerativeSearches
    model: Dict[str, Any]


GenerativeConfig = _GenerativeConfig


@dataclass
class _VectorizerConfig(_ConfigBase):
    vectorizer: Vectorizers
    model: Dict[str, Any]
    vectorize_collection_name: bool


VectorizerConfig = _VectorizerConfig


@dataclass
class _RerankerConfig(_ConfigBase):
    model: Dict[str, Any]
    reranker: Rerankers


RerankerConfig = _RerankerConfig


@dataclass
class _NamedVectorizerConfig(_ConfigBase):
    vectorizer: Vectorizers
    model: Dict[str, Any]
    source_properties: Optional[List[str]]

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["properties"] = ret_dict.pop("sourceProperties", None)
        return ret_dict


@dataclass
class _NamedVectorConfig(_ConfigBase):
    vectorizer: _NamedVectorizerConfig
    vector_index_config: Union[VectorIndexConfigHNSW, VectorIndexConfigFlat]

    def to_dict(self) -> Dict:
        ret_dict = super().to_dict()
        ret_dict["vectorIndexType"] = self.vector_index_config.vector_index_type()
        return ret_dict


NamedVectorConfig = _NamedVectorConfig


@dataclass
class _CollectionConfig(_ConfigBase):
    name: str
    description: Optional[str]
    generative_config: Optional[GenerativeConfig]
    inverted_index_config: InvertedIndexConfig
    multi_tenancy_config: MultiTenancyConfig
    properties: List[PropertyConfig]
    references: List[ReferencePropertyConfig]
    replication_config: ReplicationConfig
    reranker_config: Optional[RerankerConfig]
    sharding_config: Optional[ShardingConfig]
    vector_index_config: Union[VectorIndexConfigHNSW, VectorIndexConfigFlat, None]
    vector_index_type: Optional[VectorIndexType]
    vectorizer_config: Optional[VectorizerConfig]
    vectorizer: Optional[Vectorizers]
    vector_config: Optional[Dict[str, _NamedVectorConfig]]

    def to_dict(self) -> dict:
        out = super().to_dict()
        out["class"] = out.pop("name")
        out["moduleConfig"] = {}
        for name in [
            ("generativeConfig", "generative"),
            ("vectorizerConfig", "vectorizer"),
            ("rerankerConfig", "reranker"),
        ]:
            if name[0] not in out:
                continue

            val = out.pop(name[0])
            module_name = val[name[1]]
            out["moduleConfig"][module_name] = val.get("model", {})
            vectorize_collection_name = val.get("vectorizeCollectionName", None)
            if vectorize_collection_name is not None:
                out["moduleConfig"][module_name]["vectorizeClassName"] = vectorize_collection_name

        if "vectorConfig" in out:
            for k, v in out["vectorConfig"].items():
                extra_values = v["vectorizer"].pop("model", {})
                vectorizer = v["vectorizer"].pop("vectorizer")
                out["vectorConfig"][k]["vectorizer"] = {
                    vectorizer: {**extra_values, **v["vectorizer"]}
                }

            # remove default values for single vector setup
            out.pop(
                "vectorIndexType", None
            )  # if doesn't exist (in the case of named vectors) then do nothing
            out.pop(
                "vectorIndexConfig", None
            )  # if doesn't exist (in the case of named vectors) then do nothing

        out["properties"] = [
            *[prop.to_dict() for prop in self.properties],
            *[prop.to_dict() for prop in self.references],
        ]
        out.pop("references")
        return out


CollectionConfig = _CollectionConfig


@dataclass
class _CollectionConfigSimple(_ConfigBase):
    name: str
    description: Optional[str]
    generative_config: Optional[GenerativeConfig]
    properties: List[PropertyConfig]
    references: List[ReferencePropertyConfig]
    reranker_config: Optional[RerankerConfig]
    vectorizer_config: Optional[VectorizerConfig]
    vectorizer: Optional[Vectorizers]
    vector_config: Optional[Dict[str, _NamedVectorConfig]]


CollectionConfigSimple = _CollectionConfigSimple

ShardTypes = Literal["READONLY", "READY", "INDEXING"]


@dataclass
class _ShardStatus:
    name: str
    status: ShardTypes
    vector_queue_size: int


ShardStatus = _ShardStatus

# class PropertyConfig(ConfigCreateModel):
#     indexFilterable: Optional[bool] = Field(None, alias="index_filterable")
#     indexSearchable: Optional[bool] = Field(None, alias="index_searchable")
#     tokenization: Optional[Tokenization] = None
#     description: Optional[str] = None
#     moduleConfig: Optional[ModuleConfig] = Field(None, alias="module_config")


class Property(_ConfigCreateModel):
    """This class defines the structure of a data property that a collection can have within Weaviate.

    Attributes:
        `name`
            The name of the property, REQUIRED.
        `data_type`
            The data type of the property, REQUIRED.
        `description`
            A description of the property.
        `index_filterable`
            Whether the property should be filterable in the inverted index.
        `index_searchable`
            Whether the property should be searchable in the inverted index.
        `nested_properties`
            nested properties for data type OBJECT and OBJECT_ARRAY`.
        `skip_vectorization`
            Whether to skip vectorization of the property. Defaults to `False`.
        `tokenization`
            The tokenization method to use for the inverted index. Defaults to `None`.
        `vectorize_property_name`
            Whether to vectorize the property name. Defaults to `True`.
    """

    name: str
    dataType: DataType = Field(default=..., alias="data_type")
    description: Optional[str] = Field(default=None)
    indexFilterable: Optional[bool] = Field(default=None, alias="index_filterable")
    indexSearchable: Optional[bool] = Field(default=None, alias="index_searchable")
    nestedProperties: Optional[Union["Property", List["Property"]]] = Field(
        default=None, alias="nested_properties"
    )
    skip_vectorization: bool = Field(default=False)
    tokenization: Optional[Tokenization] = Field(default=None)
    vectorize_property_name: bool = Field(default=True)

    @field_validator("name")
    def _check_name(cls, v: str) -> str:
        if v in ["id", "vector"]:
            raise ValueError(f"Property name '{v}' is reserved and cannot be used")
        return v

    def _to_dict(self, vectorizer: Optional[Vectorizers] = None) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        if vectorizer is not None and vectorizer != Vectorizers.NONE:
            ret_dict["moduleConfig"] = {
                vectorizer.value: {
                    "skip": self.skip_vectorization,
                    "vectorizePropertyName": self.vectorize_property_name,
                }
            }
        del ret_dict["skip_vectorization"]
        del ret_dict["vectorize_property_name"]
        if self.nestedProperties is not None:
            ret_dict["nestedProperties"] = (
                [prop._to_dict() for prop in self.nestedProperties]
                if isinstance(self.nestedProperties, list)
                else [self.nestedProperties._to_dict()]
            )
        return ret_dict


class _ReferencePropertyBase(_ConfigCreateModel):
    name: str

    @field_validator("name")
    def check_name(cls, v: str) -> str:
        if v in ["id", "vector"]:
            raise ValueError(f"Property name '{v}' is reserved and cannot be used")
        return v


class _ReferencePropertyMultiTarget(_ReferencePropertyBase):
    """This class defines properties that are cross references to multiple target collections.

    Use this class when you want to create a cross-reference in the collection's config that is capable
    of having cross-references to multiple other collections at once.

    Attributes:
        `name`
            The name of the property, REQUIRED.
        `target_collections`
            The names of the target collections, REQUIRED.
        `description`
            A description of the property.
    """

    target_collections: List[str]
    description: Optional[str] = Field(default=None)

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["dataType"] = [
            _capitalize_first_letter(target) for target in self.target_collections
        ]
        del ret_dict["target_collections"]
        return ret_dict


class ReferenceProperty(_ReferencePropertyBase):
    """This class defines properties that are cross references to a single target collection.

    Use this class when you want to create a cross-reference in the collection's config that is capable
    of having only cross-references to a single other collection.

    Attributes:
        `name`
            The name of the property, REQUIRED.
        `target_collection`
            The name of the target collection, REQUIRED.
        `description`
            A description of the property.
    """

    target_collection: str
    description: Optional[str] = Field(default=None)

    MultiTarget: ClassVar[Type[_ReferencePropertyMultiTarget]] = _ReferencePropertyMultiTarget

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["dataType"] = [_capitalize_first_letter(self.target_collection)]
        del ret_dict["target_collection"]
        return ret_dict


PropertyType = Union[Property, ReferenceProperty, _ReferencePropertyMultiTarget]

T = TypeVar("T", bound="_CollectionConfigCreate")


class _CollectionConfigCreate(_ConfigCreateModel):
    name: str
    properties: Optional[Sequence[Property]] = Field(default=None)
    references: Optional[List[_ReferencePropertyBase]] = Field(default=None)
    description: Optional[str] = Field(default=None)
    invertedIndexConfig: Optional[_InvertedIndexConfigCreate] = Field(
        default=None, alias="inverted_index_config"
    )
    multiTenancyConfig: Optional[_MultiTenancyConfigCreate] = Field(
        default=None, alias="multi_tenancy_config"
    )
    replicationConfig: Optional[_ReplicationConfigCreate] = Field(
        default=None, alias="replication_config"
    )
    shardingConfig: Optional[_ShardingConfigCreate] = Field(default=None, alias="sharding_config")
    vectorIndexConfig: Optional[_VectorIndexConfigCreate] = Field(
        default=None, alias="vector_index_config"
    )
    vectorizerConfig: Optional[
        Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
    ] = Field(default=_Vectorizer.none(), alias="vectorizer_config")
    generativeSearch: Optional[_GenerativeConfigCreate] = Field(
        default=None, alias="generative_config"
    )
    rerankerConfig: Optional[_RerankerConfigCreate] = Field(default=None, alias="reranker_config")

    def model_post_init(self, __context: Any) -> None:
        self.name = _capitalize_first_letter(self.name)

    @staticmethod
    def __add_to_module_config(
        return_dict: Dict[str, Any], addition_key: str, addition_val: Dict[str, Any]
    ) -> None:
        if "moduleConfig" not in return_dict:
            return_dict["moduleConfig"] = {addition_key: addition_val}
        else:
            return_dict["moduleConfig"][addition_key] = addition_val

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict: Dict[str, Any] = {}

        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if cls_field in ["name", "model", "properties", "references"] or val is None:
                continue
            elif isinstance(val, (bool, float, str, int)):
                ret_dict[cls_field] = str(val)
            elif isinstance(val, _GenerativeConfigCreate):
                self.__add_to_module_config(ret_dict, val.generative.value, val._to_dict())
            elif isinstance(val, _RerankerConfigCreate):
                self.__add_to_module_config(ret_dict, val.reranker.value, val._to_dict())
            elif isinstance(val, _VectorizerConfigCreate):
                ret_dict["vectorizer"] = val.vectorizer.value
                if val.vectorizer != Vectorizers.NONE:
                    self.__add_to_module_config(ret_dict, val.vectorizer.value, val._to_dict())
            elif isinstance(val, _VectorIndexConfigCreate):
                ret_dict["vectorIndexType"] = val.vector_index_type()
                ret_dict[cls_field] = val._to_dict()
            elif (
                isinstance(val, list)
                and len(val) > 0
                and all(isinstance(item, _NamedVectorConfigCreate) for item in val)
            ):
                val = cast(List[_NamedVectorConfigCreate], val)
                ret_dict["vectorConfig"] = {item.name: item._to_dict() for item in val}

            else:
                assert isinstance(val, _ConfigCreateModel)
                ret_dict[cls_field] = val._to_dict()
        if self.vectorIndexConfig is None and "vectorConfig" not in ret_dict:
            ret_dict["vectorIndexType"] = VectorIndexType.HNSW

        ret_dict["class"] = self.name
        self.__add_props(self.properties, ret_dict)
        self.__add_props(self.references, ret_dict)

        return ret_dict

    def __add_props(
        self,
        props: Optional[
            Union[Sequence[Union[Property, _ReferencePropertyBase]], List[_ReferencePropertyBase]]
        ],
        ret_dict: Dict[str, Any],
    ) -> None:
        if props is None:
            return
        existing_props = ret_dict.get("properties", [])
        existing_props.extend(
            [
                (
                    prop._to_dict(
                        self.vectorizerConfig.vectorizer
                        if isinstance(self.vectorizerConfig, _VectorizerConfigCreate)
                        else None
                    )
                    if isinstance(prop, Property)
                    else prop._to_dict()
                )
                for prop in props
            ]
        )
        ret_dict["properties"] = existing_props


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

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#hnsw-with-compression) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _PQConfigCreate(
            bitCompression=bit_compression,
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

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#binary-quantization) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _BQConfigCreate(
            cache=cache,
            rescoreLimit=rescore_limit,
        )


class _VectorIndex:
    Quantizer = _VectorIndexQuantizer

    @staticmethod
    def none() -> _VectorIndexConfigSkipCreate:
        """Create a `_VectorIndexConfigSkipCreate` object to be used when configuring Weaviate to not index your vectors.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.
        """
        return _VectorIndexConfigSkipCreate(
            distance=None,
            vectorCacheMaxObjects=None,
            quantizer=None,
        )

    @staticmethod
    def hnsw(
        cleanup_interval_seconds: Optional[int] = None,
        distance_metric: Optional[VectorDistances] = None,
        dynamic_ef_factor: Optional[int] = None,
        dynamic_ef_max: Optional[int] = None,
        dynamic_ef_min: Optional[int] = None,
        ef: Optional[int] = None,
        ef_construction: Optional[int] = None,
        flat_search_cutoff: Optional[int] = None,
        max_connections: Optional[int] = None,
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
    ) -> _VectorIndexConfigHNSWCreate:
        """Create a `_VectorIndexConfigHNSWCreate` object to be used when defining the HNSW vector index configuration of Weaviate.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigHNSWCreate(
            cleanupIntervalSeconds=cleanup_interval_seconds,
            distance=distance_metric,
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            dynamicEfFactor=dynamic_ef_factor,
            efConstruction=ef_construction,
            ef=ef,
            flatSearchCutoff=flat_search_cutoff,
            maxConnections=max_connections,
            vectorCacheMaxObjects=vector_cache_max_objects,
            quantizer=quantizer,
        )

    @staticmethod
    def flat(
        distance_metric: Optional[VectorDistances] = None,
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[_BQConfigCreate] = None,
    ) -> _VectorIndexConfigFlatCreate:
        """Create a `_VectorIndexConfigFlatCreate` object to be used when defining the FLAT vector index configuration of Weaviate.

        Use this method when defining the `vector_index_config` argument in `collections.create()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigFlatCreate(
            distance=distance_metric,
            vectorCacheMaxObjects=vector_cache_max_objects,
            quantizer=quantizer,
        )


class Configure:
    """Use this factory class to generate the correct object for use when using the `collections.create()` method. E.g., `.multi_tenancy()` will return a `MultiTenancyConfigCreate` object to be used in the `multi_tenancy_config` argument.

    Each class method provides options specific to the named configuration type in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications are caught before the request is sent to Weaviate.
    """

    Generative = _Generative
    Reranker = _Reranker
    Vectorizer = _Vectorizer
    VectorIndex = _VectorIndex
    NamedVectors = _NamedVectors

    @staticmethod
    def inverted_index(
        bm25_b: Optional[float] = None,
        bm25_k1: Optional[float] = None,
        cleanup_interval_seconds: Optional[int] = None,
        index_timestamps: Optional[bool] = None,
        index_property_length: Optional[bool] = None,
        index_null_state: Optional[bool] = None,
        stopwords_preset: Optional[StopwordsPreset] = None,
        stopwords_additions: Optional[List[str]] = None,
        stopwords_removals: Optional[List[str]] = None,
    ) -> _InvertedIndexConfigCreate:
        """Create an `InvertedIndexConfigCreate` object to be used when defining the configuration of the keyword searching algorithm of Weaviate.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#configure-the-inverted-index) for details!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        if bm25_b is None and bm25_k1 is not None or bm25_k1 is None and bm25_b is not None:
            raise ValueError("bm25_b and bm25_k1 must be specified together")

        return _InvertedIndexConfigCreate(
            bm25=(
                _BM25ConfigCreate(b=bm25_b, k1=bm25_k1)
                if bm25_b is not None and bm25_k1 is not None
                else None
            ),
            cleanupIntervalSeconds=cleanup_interval_seconds,
            indexTimestamps=index_timestamps,
            indexPropertyLength=index_property_length,
            indexNullState=index_null_state,
            stopwords=_StopwordsCreate(
                preset=stopwords_preset,
                additions=stopwords_additions,
                removals=stopwords_removals,
            ),
        )

    @staticmethod
    def multi_tenancy(enabled: bool = True) -> _MultiTenancyConfigCreate:
        """Create a `MultiTenancyConfigCreate` object to be used when defining the multi-tenancy configuration of Weaviate.

        Arguments:
            `enabled`
                Whether multi-tenancy is enabled. Defaults to `True`.
        """
        return _MultiTenancyConfigCreate(enabled=enabled)

    @staticmethod
    def replication(factor: Optional[int] = None) -> _ReplicationConfigCreate:
        """Create a `ReplicationConfigCreate` object to be used when defining the replication configuration of Weaviate.

        Arguments:
            `factor`
                The replication factor.
        """
        return _ReplicationConfigCreate(factor=factor)

    @staticmethod
    def sharding(
        virtual_per_physical: Optional[int] = None,
        desired_count: Optional[int] = None,
        actual_count: Optional[int] = None,
        desired_virtual_count: Optional[int] = None,
        actual_virtual_count: Optional[int] = None,
    ) -> _ShardingConfigCreate:
        """Create a `ShardingConfigCreate` object to be used when defining the sharding configuration of Weaviate.

        NOTE: You can only use one of Sharding or Replication, not both.

        See [the docs](https://weaviate.io/developers/weaviate/concepts/replication-architecture#replication-vs-sharding) for more details.

        Arguments:
            `virtual_per_physical`
                The number of virtual shards per physical shard.
            `desired_count`
                The desired number of physical shards.
            `actual_count`
                The actual number of physical shards.
            `desired_virtual_count`
                The desired number of virtual shards.
            `actual_virtual_count`
                The actual number of virtual shards.
        """
        return _ShardingConfigCreate(
            virtualPerPhysical=virtual_per_physical,
            desiredCount=desired_count,
            actualCount=actual_count,
            desiredVirtualCount=desired_virtual_count,
            actualVirtualCount=actual_virtual_count,
        )


class _VectorIndexQuantizerUpdate:
    @staticmethod
    def pq(
        bit_compression: Optional[bool] = None,
        centroids: Optional[int] = None,
        encoder_distribution: Optional[PQEncoderDistribution] = None,
        encoder_type: Optional[PQEncoderType] = None,
        segments: Optional[int] = None,
        training_limit: Optional[int] = None,
        enabled: bool = True,
    ) -> _PQConfigUpdate:
        """Create a `_PQConfigUpdate` object to be used when updating the product quantization (PQ) configuration of Weaviate.

        Use this method when defining the `quantizer` argument in the `vector_index` configuration in `collection.update()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#hnsw-with-compression) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _PQConfigUpdate(
            enabled=enabled,
            bitCompression=bit_compression,
            centroids=centroids,
            segments=segments,
            trainingLimit=training_limit,
            encoder=(
                _PQEncoderConfigUpdate(type_=encoder_type, distribution=encoder_distribution)
                if encoder_type is not None or encoder_distribution is not None
                else None
            ),
        )

    @staticmethod
    def bq(rescore_limit: Optional[int] = None) -> _BQConfigUpdate:
        """Create a `_BQConfigUpdate` object to be used when updating the binary quantization (BQ) configuration of Weaviate.

        Use this method when defining the `quantizer` argument in the `vector_index` configuration in `collection.update()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/concepts/vector-index#hnsw-with-compression) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _BQConfigUpdate(rescoreLimit=rescore_limit)


class _VectorIndexUpdate:
    Quantizer = _VectorIndexQuantizerUpdate

    @staticmethod
    def hnsw(
        dynamic_ef_factor: Optional[int] = None,
        dynamic_ef_min: Optional[int] = None,
        dynamic_ef_max: Optional[int] = None,
        ef: Optional[int] = None,
        flat_search_cutoff: Optional[int] = None,
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[Union[_PQConfigUpdate, _BQConfigUpdate]] = None,
    ) -> _VectorIndexConfigHNSWUpdate:
        """Create an `_VectorIndexConfigHNSWUpdate` object to update the configuration of the HNSW vector index.

        Use this method when defining the `vector_index_config` argument in `collection.update()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#configure-the-inverted-index) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigHNSWUpdate(
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            dynamicEfFactor=dynamic_ef_factor,
            ef=ef,
            flatSearchCutoff=flat_search_cutoff,
            vectorCacheMaxObjects=vector_cache_max_objects,
            quantizer=quantizer,
        )

    @staticmethod
    def flat(
        vector_cache_max_objects: Optional[int] = None,
        quantizer: Optional[_BQConfigUpdate] = None,
    ) -> _VectorIndexConfigFlatUpdate:
        """Create an `_VectorIndexConfigFlatUpdate` object to update the configuration of the FLAT vector index.

        Use this method when defining the `vector_index_config` argument in `collection.update()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#configure-the-inverted-index) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigFlatUpdate(
            vectorCacheMaxObjects=vector_cache_max_objects,
            quantizer=quantizer,
        )


class Reconfigure:
    """Use this factory class to generate the correct `xxxConfig` object for use when using the `collection.update()` method.

    Each staticmethod provides options specific to the named configuration type in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications are caught before the request is sent to Weaviate. Only those configurations that are mutable are
    available in this class. If you wish to update the configuration of an immutable aspect of your collection then you will have to delete
    the collection and re-create it with the new configuration.
    """

    NamedVectors = _NamedVectorsUpdate
    VectorIndex = _VectorIndexUpdate

    @staticmethod
    def inverted_index(
        bm25_b: Optional[float] = None,
        bm25_k1: Optional[float] = None,
        cleanup_interval_seconds: Optional[int] = None,
        stopwords_additions: Optional[List[str]] = None,
        stopwords_preset: Optional[StopwordsPreset] = None,
        stopwords_removals: Optional[List[str]] = None,
    ) -> _InvertedIndexConfigUpdate:
        """Create an `InvertedIndexConfigUpdate` object.

        Use this method when defining the `inverted_index_config` argument in `collection.update()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#configure-the-inverted-index) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _InvertedIndexConfigUpdate(
            bm25=_BM25ConfigUpdate(b=bm25_b, k1=bm25_k1),
            cleanupIntervalSeconds=cleanup_interval_seconds,
            stopwords=_StopwordsUpdate(
                preset=stopwords_preset,
                additions=stopwords_additions,
                removals=stopwords_removals,
            ),
        )

    @staticmethod
    def replication(factor: Optional[int] = None) -> _ReplicationConfigUpdate:
        """Create a `ReplicationConfigUpdate` object.

        Use this method when defining the `replication_config` argument in `collection.update()`.

        Arguments:
            `factor`
                The replication factor.
        """
        return _ReplicationConfigUpdate(factor=factor)

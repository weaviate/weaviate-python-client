from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, cast

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from weaviate.util import _capitalize_first_letter
from weaviate.warnings import _Warnings


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


class _VectorIndexType(str, Enum):
    HNSW = "hnsw"


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
    """

    WORD = "word"
    WHITESPACE = "whitespace"
    LOWERCASE = "lowercase"
    FIELD = "field"


class Vectorizer(str, Enum):
    """The available vectorization modules in Weaviate.

    These modules encode binary data into lists of floats called vectors.
    See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules) for more details.

    Attributes:
        `NONE`
            No vectorizer.
        `TEXT2VEC_COHERE`
            Weaviate module backed by Cohere text-based embedding models.
        `TEXT2VEC_CONTEXTIONARY`
            Weaviate module backed by Contextionary text-based embedding models.
        `TEXT2VEC_GPT4ALL`
            Weaviate module backed by GPT-4-All text-based embedding models.
        `TEXT2VEC_HUGGINGFACE`
            Weaviate module backed by HuggingFace text-based embedding models.
        `TEXT2VEC_OPENAI`
            Weaviate module backed by OpenAI and Azure-OpenAI text-based embedding models.
        `TEXT2VEC_PALM`
            Weaviate module backed by PaLM text-based embedding models.
        `TEXT2VEC_TRANSFORMERS`
            Weaviate module backed by Transformers text-based embedding models.
        `IMG2VEC_NEURAL`
            Weaviate module backed by a ResNet-50 neural network for images.
        `MULTI2VEC_CLIP`
            Weaviate module backed by a Sentence-BERT CLIP model for images and text.
        `MULTI2VEC_BIND`
            Weaviate module backed by the ImageBind model for images, text, audio, depth, IMU, thermal, and video.
        `REF2VEC_CENTROID`
            Weaviate module backed by a centroid-based model that calculates an object's vectors from its referenced vectors.
    """

    NONE = "none"
    TEXT2VEC_COHERE = "text2vec-cohere"
    TEXT2VEC_CONTEXTIONARY = "text2vec-contextionary"
    TEXT2VEC_GPT4ALL = "text2vec-gpt4all"
    TEXT2VEC_HUGGINGFACE = "text2vec-huggingface"
    TEXT2VEC_OPENAI = "text2vec-openai"
    TEXT2VEC_PALM = "text2vec-palm"
    TEXT2VEC_TRANSFORMERS = "text2vec-transformers"
    IMG2VEC_NEURAL = "img2vec-neural"
    MULTI2VEC_CLIP = "multi2vec-clip"
    MULTI2VEC_BIND = "multi2vec-bind"
    REF2VEC_CENTROID = "ref2vec-centroid"


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
    """

    OPENAI = "generative-openai"
    COHERE = "generative-cohere"
    PALM = "generative-palm"


class VectorDistance(str, Enum):
    """Vector similarity distance metric to be used in the `VectorIndexConfig` class.

    To ensure optimal search results, we recommend reviewing whether your model provider advises a
    specific distance metric and following their advice.

    Attributes:
        `COSINE`
            Cosine distance: [reference](https://en.wikipedia.org/wiki/Cosine_similarity)
        `DOT`
            Dot distance: [reference](https://en.wikipedia.org/wiki/Dot_product)
        `L2_SQUARED`
            L2 squared distance: [reference](https://en.wikipedia.org/wiki/Euclidean_distance)
        `HAMMING`
            Hamming distance: [reference](https://en.wikipedia.org/wiki/Hamming_distance)
        `MANHATTAN`
            Manhattan distance: [reference](https://en.wikipedia.org/wiki/Taxicab_geometry)
    """

    COSINE = "cosine"
    DOT = "dot"
    L2_SQUARED = "l2-squared"
    HAMMING = "hamming"
    MANHATTAN = "manhattan"


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


class _ConfigCreateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def _to_dict(self) -> Dict[str, Any]:
        return cast(dict, self.model_dump(exclude_none=True))


class _ConfigUpdateModel(BaseModel):
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
                assert isinstance(val, _ConfigUpdateModel)
                schema[cls_field] = val.merge_with_existing(schema[cls_field])
        return schema


class _PQEncoderConfigCreate(_ConfigCreateModel):
    type_: PQEncoderType
    distribution: PQEncoderDistribution

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["type"] = ret_dict.pop("type_")
        return ret_dict


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


class _PQConfigCreate(_ConfigCreateModel):
    bitCompression: bool
    centroids: int
    enabled: bool
    encoder: _PQEncoderConfigCreate
    segments: int
    trainingLimit: int = Field(..., ge=100000)

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["encoder"] = {
            "type": ret_dict.pop("encoder_type"),
            "distribution": ret_dict.pop("encoder_distribution"),
        }
        return ret_dict


class _PQConfigUpdate(_ConfigUpdateModel):
    bitCompression: Optional[bool]
    centroids: Optional[int]
    enabled: Optional[bool]
    segments: Optional[int]
    trainingLimit: Optional[int]
    encoder: Optional[_PQEncoderConfigUpdate]


class _VectorIndexConfigCreate(_ConfigCreateModel):
    cleanupIntervalSeconds: int
    distance: VectorDistance
    dynamicEfMin: int
    dynamicEfMax: int
    dynamicEfFactor: int
    efConstruction: int
    ef: int
    flatSearchCutoff: int
    maxConnections: int
    pq: _PQConfigCreate
    skip: bool
    vectorCacheMaxObjects: int


class _VectorIndexConfigUpdate(_ConfigUpdateModel):
    dynamicEfFactor: Optional[int]
    dynamicEfMin: Optional[int]
    dynamicEfMax: Optional[int]
    ef: Optional[int]
    flatSearchCutoff: Optional[int]
    skip: Optional[bool]
    vectorCacheMaxObjects: Optional[int]
    pq: Optional[_PQConfigUpdate]


class _ShardingConfigCreate(_ConfigCreateModel):
    virtualPerPhysical: int
    desiredCount: int
    actualCount: int
    desiredVirtualCount: int
    actualVirtualCount: int
    key: str = "_id"
    strategy: str = "hash"
    function: str = "murmur3"


class _ReplicationConfigCreate(_ConfigCreateModel):
    factor: int


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
    bm25: _BM25ConfigCreate
    cleanupIntervalSeconds: int
    indexTimestamps: bool
    indexPropertyLength: bool
    indexNullState: bool
    stopwords: _StopwordsCreate


class _InvertedIndexConfigUpdate(_ConfigUpdateModel):
    bm25: Optional[_BM25ConfigUpdate]
    cleanupIntervalSeconds: Optional[int]
    stopwords: Optional[_StopwordsUpdate]


class _MultiTenancyConfigCreate(_ConfigCreateModel):
    enabled: bool = False


class _MultiTenancyConfigUpdate(_ConfigUpdateModel):
    enabled: Optional[bool] = None


class _GenerativeConfig(_ConfigCreateModel):
    generative: GenerativeSearches


class _GenerativeOpenAIConfigBase(_GenerativeConfig):
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


class _GenerativeCohereConfig(_GenerativeConfig):
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


class _GenerativePaLMConfig(_GenerativeConfig):
    generative: GenerativeSearches = Field(
        default=GenerativeSearches.PALM, frozen=True, exclude=True
    )
    apiEndpoint: Optional[AnyHttpUrl]
    maxOutputTokens: Optional[int]
    modelId: Optional[str]
    projectId: str
    temperature: Optional[float]
    topK: Optional[int]
    topP: Optional[float]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.apiEndpoint is not None:
            ret_dict["apiEndpoint"] = self.apiEndpoint.unicode_string()
        return ret_dict


class _VectorizerConfig(_ConfigCreateModel):
    vectorizer: Vectorizer


class _Generative:
    """Use this factory class to create the correct object for the `generative_config` argument in the `collection.create()` method.

    Each staticmethod provides options specific to the named generative search module in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @staticmethod
    def openai(
        model: Optional[str] = None,
        frequency_penalty: Optional[float] = None,
        max_tokens: Optional[int] = None,
        presence_penalty: Optional[float] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _GenerativeConfig:
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
    ) -> _GenerativeConfig:
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
        model: Optional[str] = None,
        k: Optional[int] = None,
        max_tokens: Optional[int] = None,
        return_likelihoods: Optional[str] = None,
        stop_sequences: Optional[List[str]] = None,
        temperature: Optional[float] = None,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _GenerativeConfig:
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
        api_endpoint: Optional[AnyHttpUrl] = None,
        max_output_tokens: Optional[int] = None,
        model_id: Optional[str] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> _GenerativeConfig:
        """Create a `_GenerativePaLMConfig` object for use when performing AI generation using the `generative-palm` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-palm)
        for detailed usage.

        Arguments:
            `project_id`
                The PalM project ID to use.
            `api_endpoint`
                The API endpoint to use. Defaults to `None`, which uses the server-defined default
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


class _Text2VecAzureOpenAIConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_OPENAI, frozen=True, exclude=True)
    baseURL: Optional[AnyHttpUrl]
    resourceName: str
    deploymentId: str
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Text2VecContextionaryConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_CONTEXTIONARY, frozen=True, exclude=True
    )
    vectorizeClassName: bool


CohereModel = Literal[
    "embed-multilingual-v2.0",
    "embed-multilingual-v3.0",
    "small",
    "medium",
    "large",
    "multilingual-22-12",
    "embed-english-v2.0",
    "embed-english-light-v2.0",
]
CohereTruncation = Literal["RIGHT", "NONE"]


class _Text2VecCohereConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_COHERE, frozen=True, exclude=True)
    baseURL: Optional[AnyHttpUrl]
    model: Optional[CohereModel]
    truncate: Optional[CohereTruncation]
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Text2VecHuggingFaceConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_HUGGINGFACE, frozen=True, exclude=True
    )
    model: Optional[str]
    passageModel: Optional[str]
    queryModel: Optional[str]
    endpointURL: Optional[AnyHttpUrl]
    waitForModel: Optional[bool]
    useGPU: Optional[bool]
    useCache: Optional[bool]
    vectorizeClassName: bool

    def validate_mutually_exclusive_fields(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "passageModel" in values and "queryModel" not in values:
            raise ValueError("Must specify query_model when specifying passage_model")
        if "queryModel" in values and "passageModel" not in values:
            raise ValueError("Must specify passage_model when specifying query_model")
        if "model" in values and any(["passageModel" in values, "queryModel" in values]):
            raise ValueError(
                "Can only specify model alone or passage_model and query_model together"
            )
        if (
            any(["passageModel" in values, "queryModel" in values, "model" in values])
            and "endpointURL" in values
        ):
            _Warnings.text2vec_huggingface_endpoint_url_and_model_set_together()
        if all(
            [
                "passageModel" not in values,
                "queryModel" not in values,
                "model" not in values,
                "endpointURL" not in values,
            ]
        ):
            raise ValueError(
                "Must specify at least one of model, passage_model & query_model, or endpoint_url"
            )
        return values

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        options = {}
        if self.waitForModel is not None:
            options["waitForModel"] = ret_dict.pop("waitForModel")
        if self.useGPU is not None:
            options["useGPU"] = ret_dict.pop("useGPU")
        if self.useCache is not None:
            options["useCache"] = ret_dict.pop("useCache")
        if len(options) > 0:
            ret_dict["options"] = options
        if self.endpointURL is not None:
            ret_dict["endpointURL"] = self.endpointURL.unicode_string()
        return ret_dict


OpenAIModel = Literal["ada", "babbage", "curie", "davinci"]
OpenAIType = Literal["text", "code"]


class _Text2VecOpenAIConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_OPENAI, frozen=True, exclude=True)
    baseURL: Optional[AnyHttpUrl]
    model: Optional[OpenAIModel]
    modelVersion: Optional[str]
    type_: Optional[OpenAIType]
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.type_ is not None:
            ret_dict["type"] = ret_dict.pop("type_")
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Text2VecPalmConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_PALM, frozen=True, exclude=True)
    projectId: str
    apiEndpoint: Optional[AnyHttpUrl]
    modelId: Optional[str]
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.apiEndpoint is not None:
            ret_dict["apiEndpoint"] = self.apiEndpoint.unicode_string()
        return ret_dict


class _Text2VecTransformersConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_TRANSFORMERS, frozen=True, exclude=True
    )
    poolingStrategy: Literal["masked_mean", "cls"]
    vectorizeClassName: bool


class _Text2VecGPT4AllConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_GPT4ALL, frozen=True, exclude=True)
    vectorizeClassName: bool


class _Img2VecNeuralConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.IMG2VEC_NEURAL, frozen=True, exclude=True)
    imageFields: List[str]


class Multi2VecField(BaseModel):
    """Use this class when defining the fields to use in the `Multi2VecClip` and `Multi2VecBind` vectorizers."""

    name: str
    weight: Optional[float] = Field(default=None, exclude=True)


class _Multi2VecBase(_VectorizerConfig):
    imageFields: Optional[List[Multi2VecField]]
    textFields: Optional[List[Multi2VecField]]
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["weights"] = {}
        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if "Fields" in cls_field and val is not None:
                val = cast(List[Multi2VecField], val)
                ret_dict[cls_field] = [field.name for field in val]
                weights = [field.weight for field in val if field.weight is not None]
                if len(weights) > 0:
                    ret_dict["weights"][cls_field] = weights
        if len(ret_dict["weights"]) == 0:
            del ret_dict["weights"]
        return ret_dict


class _Multi2VecClipConfig(_Multi2VecBase):
    vectorizer: Vectorizer = Field(default=Vectorizer.MULTI2VEC_CLIP, frozen=True, exclude=True)


class _Multi2VecBindConfig(_Multi2VecBase):
    vectorizer: Vectorizer = Field(default=Vectorizer.MULTI2VEC_BIND, frozen=True, exclude=True)
    audioFields: Optional[List[Multi2VecField]]
    depthFields: Optional[List[Multi2VecField]]
    IMUFields: Optional[List[Multi2VecField]]
    thermalFields: Optional[List[Multi2VecField]]
    videoFields: Optional[List[Multi2VecField]]


class _Ref2VecCentroidConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.REF2VEC_CENTROID, frozen=True, exclude=True)
    referenceProperties: List[str]
    method: Literal["mean"]


class _Vectorizer:
    """Use this factory class to create the correct object for the `vectorizer_config` argument in the `collection.create()` method.

    Each staticmethod provides options specific to the named vectorizer in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @staticmethod
    def none() -> _VectorizerConfig:
        """Create a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`."""
        return _VectorizerConfig(vectorizer=Vectorizer.NONE)

    @staticmethod
    def img2vec_neural(
        image_fields: List[str],
    ) -> _VectorizerConfig:
        """Create a `Img2VecNeuralConfig` object for use when vectorizing using the `img2vec-neural` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/img2vec-neural)
        for detailed usage.

        Arguments:
            `image_fields`
                The image fields to use. This is a required field and must match the property fields
                of the collection that are defined as `DataType.BLOB`.

        Raises:
            `pydantic.ValidationError` if `image_fields` is not a `list`.
        """
        return _Img2VecNeuralConfig(imageFields=image_fields)

    @staticmethod
    def multi2vec_clip(
        image_fields: Optional[List[Multi2VecField]] = None,
        text_fields: Optional[List[Multi2VecField]] = None,
        vectorize_class_name: bool = True,
    ) -> _VectorizerConfig:
        """Create a `Multi2VecClipConfig` object for use when vectorizing using the `multi2vec-clip` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-clip)
        for detailed usage.

        Arguments:
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `image_fields` or `text_fields` are not `None` or a `list`.
        """
        return _Multi2VecClipConfig(
            imageFields=image_fields,
            textFields=text_fields,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def multi2vec_bind(
        audio_fields: Optional[List[Multi2VecField]] = None,
        depth_fields: Optional[List[Multi2VecField]] = None,
        image_fields: Optional[List[Multi2VecField]] = None,
        imu_fields: Optional[List[Multi2VecField]] = None,
        text_fields: Optional[List[Multi2VecField]] = None,
        thermal_fields: Optional[List[Multi2VecField]] = None,
        video_fields: Optional[List[Multi2VecField]] = None,
        vectorize_class_name: bool = True,
    ) -> _VectorizerConfig:
        """Create a `Multi2VecClipConfig` object for use when vectorizing using the `multi2vec-clip` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind)
        for detailed usage.

        Arguments:
            `audio_fields`
                The audio fields to use in vectorization.
            `depth_fields`
                The depth fields to use in vectorization.
            `image_fields`
                The image fields to use in vectorization.
            `imu_fields`
                The IMU fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.
            `thermal_fields`
                The thermal fields to use in vectorization.
            `video_fields`
                The video fields to use in vectorization.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if any of the `*_fields` are not `None` or a `list`.
        """
        return _Multi2VecBindConfig(
            audioFields=audio_fields,
            depthFields=depth_fields,
            imageFields=image_fields,
            IMUFields=imu_fields,
            textFields=text_fields,
            thermalFields=thermal_fields,
            videoFields=video_fields,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def ref2vec_centroid(
        reference_properties: List[str],
        method: Literal["mean"] = "mean",
    ) -> _VectorizerConfig:
        """Create a `Ref2VecCentroidConfig` object for use when vectorizing using the `ref2vec-centroid` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/ref2vec-centroid)
        for detailed usage.

        Arguments:
            `reference_properties`
                The reference properties to use in vectorization, REQUIRED.
            `method`
                The method to use in vectorization. Defaults to `mean`.

        Raises:
            `pydantic.ValidationError` if `reference_properties` is not a `list`.
        """
        return _Ref2VecCentroidConfig(
            referenceProperties=reference_properties,
            method=method,
        )

    @staticmethod
    def text2vec_azure_openai(
        resource_name: str,
        deployment_id: str,
        vectorize_class_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _VectorizerConfig:
        """Create a `Text2VecAzureOpenAIConfig` object for use when vectorizing using the `text2vec-azure-openai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-azure-openai)
        for detailed usage.

        Arguments:
            `resource_name`
                The resource name to use, REQUIRED.
            `deployment_id`
                The deployment ID to use, REQUIRED.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `resource_name` or `deployment_id` are not `str`.
        """
        return _Text2VecAzureOpenAIConfig(
            baseURL=base_url,
            resourceName=resource_name,
            deploymentId=deployment_id,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def text2vec_contextionary(vectorize_class_name: bool = True) -> _VectorizerConfig:
        """Create a `Text2VecContextionaryConfig` object for use when vectorizing using the `text2vec-contextionary` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-contextionary)
        for detailed usage.

        Arguments:
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError`` if `vectorize_class_name` is not a `bool`.
        """
        return _Text2VecContextionaryConfig(vectorizeClassName=vectorize_class_name)

    @staticmethod
    def text2vec_cohere(
        model: Optional[CohereModel] = None,
        truncate: Optional[CohereTruncation] = None,
        vectorize_class_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _VectorizerConfig:
        """Create a `Text2VecCohereConfig` object for use when vectorizing using the `text2vec-cohere` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-cohere)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `truncate`
                The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `model` or `truncate` are not valid values from the `CohereModel` and `CohereTruncate` types.
        """
        return _Text2VecCohereConfig(
            baseURL=base_url,
            model=model,
            truncate=truncate,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def text2vec_gpt4all(
        vectorize_class_name: bool = True,
    ) -> _VectorizerConfig:
        """Create a `Text2VecGPT4AllConfig` object for use when vectorizing using the `text2vec-gpt4all` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `vectorize_class_name` is not a `bool`.
        """
        return _Text2VecGPT4AllConfig(vectorizeClassName=vectorize_class_name)

    @staticmethod
    def text2vec_huggingface(
        model: Optional[str] = None,
        passage_model: Optional[str] = None,
        query_model: Optional[str] = None,
        endpoint_url: Optional[AnyHttpUrl] = None,
        wait_for_model: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        vectorize_class_name: bool = True,
    ) -> _VectorizerConfig:
        """Create a `Text2VecHuggingFaceConfig` object for use when vectorizing using the `text2vec-huggingface` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `passage_model`
                The passage model to use. Defaults to `None`, which uses the server-defined default.
            `query_model`
                The query model to use. Defaults to `None`, which uses the server-defined default.
            `endpoint_url`
                The endpoint URL to use. Defaults to `None`, which uses the server-defined default.
            `wait_for_model`
                Whether to wait for the model to be loaded. Defaults to `None`, which uses the server-defined default.
            `use_gpu`
                Whether to use the GPU. Defaults to `None`, which uses the server-defined default.
            `use_cache`
                Whether to use the cache. Defaults to `None`, which uses the server-defined default.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if the arguments passed to the function are invalid.
                It is important to note that some of these variables are mutually exclusive.
                    See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface) for more details.
        """
        return _Text2VecHuggingFaceConfig(
            model=model,
            passageModel=passage_model,
            queryModel=query_model,
            endpointURL=endpoint_url,
            waitForModel=wait_for_model,
            useGPU=use_gpu,
            useCache=use_cache,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def text2vec_openai(
        model: Optional[OpenAIModel] = None,
        model_version: Optional[str] = None,
        type_: Optional[OpenAIType] = None,
        vectorize_class_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _VectorizerConfig:
        """Create a `Text2VecOpenAIConfig` object for use when vectorizing using the `text2vec-openai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-openai)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `model_version`
                The model version to use. Defaults to `None`, which uses the server-defined default.
            `type_`
                The type of model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `model` or `type_` are not valid values from the `OpenAIModel` and `OpenAIType` types.
        """
        return _Text2VecOpenAIConfig(
            baseURL=base_url,
            model=model,
            modelVersion=model_version,
            type_=type_,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def text2vec_palm(
        project_id: str,
        api_endpoint: Optional[AnyHttpUrl] = None,
        model_id: Optional[str] = None,
        vectorize_class_name: bool = True,
    ) -> _VectorizerConfig:
        """Create a `Text2VecPalmConfig` object for use when vectorizing using the `text2vec-palm` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-palm)
        for detailed usage.

        Arguments:
            `project_id`
                The project ID to use, REQUIRED.
            `api_endpoint`
                The API endpoint to use. Defaults to `None`, which uses the server-defined default.
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        return _Text2VecPalmConfig(
            projectId=project_id,
            apiEndpoint=api_endpoint,
            modelId=model_id,
            vectorizeClassName=vectorize_class_name,
        )

    @staticmethod
    def text2vec_transformers(
        pooling_strategy: Literal["masked_mean", "cls"] = "masked_mean",
        vectorize_class_name: bool = True,
    ) -> _VectorizerConfig:
        """Create a `Text2VecTransformersConfig` object for use when vectorizing using the `text2vec-transformers` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-transformers)
        for detailed usage.

        Arguments:
            `pooling_strategy`
                The pooling strategy to use. Defaults to `masked_mean`.
            `vectorize_class_name`
                Whether to vectorize the class name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `pooling_strategy` is not a valid value from the `PoolingStrategy` type.
        """
        return _Text2VecTransformersConfig(
            poolingStrategy=pooling_strategy,
            vectorizeClassName=vectorize_class_name,
        )


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
    vectorIndexType: _VectorIndexType = Field(
        default=_VectorIndexType.HNSW, alias="vector_index_type"
    )
    moduleConfig: _VectorizerConfig = Field(default=_Vectorizer.none(), alias="vectorizer_config")
    generativeSearch: Optional[_GenerativeConfig] = Field(default=None, alias="generative_config")

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict: Dict[str, Any] = {}

        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if cls_field in ["name", "model", "properties"] or val is None:
                continue
            if isinstance(val, Enum):
                ret_dict[cls_field] = str(val.value)
            elif isinstance(val, (bool, float, str, int)):
                ret_dict[cls_field] = str(val)
            elif isinstance(val, _GenerativeConfig):
                self.__add_to_module_config(ret_dict, val.generative.value, val._to_dict())
            elif isinstance(val, _VectorizerConfig):
                ret_dict["vectorizer"] = val.vectorizer.value
                if val.vectorizer != Vectorizer.NONE:
                    self.__add_to_module_config(ret_dict, val.vectorizer.value, val._to_dict())
            else:
                assert isinstance(val, _ConfigCreateModel)
                ret_dict[cls_field] = val._to_dict()
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
    index_null_state: bool
    index_property_length: bool
    index_timestamps: bool
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
class _ReplicationConfig:
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
    distance_metric: VectorDistance
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
    replication_config: _ReplicationConfig
    sharding_config: _ShardingConfig
    vector_index_config: _VectorIndexConfig
    vector_index_type: _VectorIndexType
    vectorizer: Vectorizer


@dataclass
class _CollectionConfigSimple:
    name: str
    description: Optional[str]
    properties: List[_Property]
    vectorizer: Vectorizer


@dataclass
class _ShardStatus:
    name: str
    status: Literal["READONLY", "READY", "INDEXING"]
    vector_queue_size: int


# class PropertyConfig(ConfigCreateModel):
#     indexFilterable: Optional[bool] = Field(None, alias="index_filterable")
#     indexSearchable: Optional[bool] = Field(None, alias="index_searchable")
#     tokenization: Optional[Tokenization] = None
#     description: Optional[str] = None
#     moduleConfig: Optional[ModuleConfig] = Field(None, alias="module_config")


@dataclass
class PropertyConfig:  # noqa
    index_filterable: Optional[bool] = None
    index_searchable: Optional[bool] = None
    tokenization: Optional[Tokenization] = None
    description: Optional[str] = None
    vectorizer_config: Optional[_VectorizerConfig] = None

    # tmp solution. replace with a pydantic BaseModel, see bugreport: https://github.com/pydantic/pydantic/issues/6948
    # bugreport was closed as not planned :( so dataclasses must stay
    def _to_dict(self) -> Dict[str, Any]:
        return {
            "indexFilterable": self.index_filterable,
            "indexSearchable": self.index_searchable,
            "tokenization": self.tokenization,
            "description": self.description,
            "moduleConfig": self.vectorizer_config,
        }


class Property(_ConfigCreateModel):
    """This class defines the structure of a data property that a collection can have within Weaviate.

    Attributes:
        `name`
            The name of the property, REQUIRED.
        `data_type`
            The data type of the property, REQUIRED.
        `index_filterable`
            Whether the property should be filterable in the inverted index.
        `index_searchable`
            Whether the property should be searchable in the inverted index.
        `description`
            A description of the property.
        `skip_vectorization`
            Whether to skip vectorization of the property. Defaults to `False`.
        `tokenization`
            The tokenization method to use for the inverted index. Defaults to `None`.
        `vectorize_property_name`
            Whether to vectorize the property name. Defaults to `True`.
    """

    name: str
    dataType: DataType = Field(default=..., alias="data_type")
    indexFilterable: Optional[bool] = Field(default=None, alias="index_filterable")
    indexSearchable: Optional[bool] = Field(default=None, alias="index_searchable")
    description: Optional[str] = Field(default=None)
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

    def _to_dict(self, vectorizer: Optional[Vectorizer] = None) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        if vectorizer is not None and vectorizer != Vectorizer.NONE:
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


class ReferenceProperty(_ReferencePropertyBase):
    """This class defines properties that are cross references to a single target collection.

    Use this class when you want to create a cross-reference in the collection's config that is capable
    of having only cross-references to a single other collection.

    Attributes:
        `name`
            The name of the property, REQUIRED.
        `target_collection`
            The name of the target collection, REQUIRED.
    """

    target_collection: str

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["dataType"] = [_capitalize_first_letter(self.target_collection)]
        del ret_dict["target_collection"]
        return ret_dict


class ReferencePropertyMultiTarget(_ReferencePropertyBase):
    """This class defines properties that are cross references to multiple target collections.

    Use this class when you want to create a cross-reference in the collection's config that is capable
    of having cross-references to multiple other collections at once.

    Attributes:
        `name`
            The name of the property, REQUIRED.
        `target_collections`
            The names of the target collections, REQUIRED.
    """

    target_collections: List[str]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        ret_dict["dataType"] = [
            _capitalize_first_letter(target) for target in self.target_collections
        ]
        del ret_dict["target_collections"]
        return ret_dict


PropertyType = Union[Property, ReferenceProperty, ReferencePropertyMultiTarget]


class _CollectionConfigCreate(_CollectionConfigCreateBase):
    name: str
    properties: Optional[List[Union[Property, _ReferencePropertyBase]]] = Field(default=None)

    def model_post_init(self, __context: Any) -> None:
        self.name = _capitalize_first_letter(self.name)

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()

        ret_dict["class"] = self.name

        if self.properties is not None:
            ret_dict["properties"] = [
                prop._to_dict(self.moduleConfig.vectorizer)
                if isinstance(prop, Property)
                else prop._to_dict()
                for prop in self.properties
            ]

        return ret_dict


class Configure:
    """Use this factory class to generate the correct object for use when using the `collection.create()` method. E.g., `.multi_tenancy()` will return a `MultiTenancyConfigCreate` object to be used in the `multi_tenancy_config` argument.

    Each class method provides options specific to the named configuration type in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications are caught before the request is sent to Weaviate.
    """

    Generative = _Generative
    Vectorizer = _Vectorizer

    @staticmethod
    def inverted_index(
        bm25_b: float = 0.75,
        bm25_k1: float = 1.2,
        cleanup_interval_seconds: int = 60,
        index_timestamps: bool = False,
        index_property_length: bool = False,
        index_null_state: bool = False,
        stopwords_preset: Optional[StopwordsPreset] = None,
        stopwords_additions: Optional[List[str]] = None,
        stopwords_removals: Optional[List[str]] = None,
    ) -> _InvertedIndexConfigCreate:
        """Create an `InvertedIndexConfigCreate` object to be used when defining the configuration of the keyword searching algorithm of Weaviate.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#configure-the-inverted-index) for details!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _InvertedIndexConfigCreate(
            bm25=_BM25ConfigCreate(b=bm25_b, k1=bm25_k1),
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
    def multi_tenancy(enabled: bool = False) -> _MultiTenancyConfigCreate:
        """Create a `MultiTenancyConfigCreate` object to be used when defining the multi-tenancy configuration of Weaviate.

        Arguments:
            `enabled`
                Whether multi-tenancy is enabled. Defaults to `False`.
        """
        return _MultiTenancyConfigCreate(enabled=enabled)

    @staticmethod
    def replication(factor: int = 1) -> _ReplicationConfigCreate:
        """Create a `ReplicationConfigCreate` object to be used when defining the replication configuration of Weaviate.

        Arguments:
            `factor`
                The replication factor. Defaults to `1`.
        """
        return _ReplicationConfigCreate(factor=factor)

    @staticmethod
    def sharding(
        virtual_per_physical: int = 128,
        desired_count: int = 1,
        actual_count: int = 1,
        desired_virtual_count: int = 128,
        actual_virtual_count: int = 128,
    ) -> _ShardingConfigCreate:
        """Create a `ShardingConfigCreate` object to be used when defining the sharding configuration of Weaviate.

        NOTE: You can only use one of Sharding or Replication, not both.

        See [the docs](https://weaviate.io/developers/weaviate/concepts/replication-architecture#replication-vs-sharding) for more details.

        Arguments:
            `virtual_per_physical`
                The number of virtual shards per physical shard. Defaults to `128`.
            `desired_count`
                The desired number of physical shards. Defaults to `1`.
            `actual_count`
                The actual number of physical shards. Defaults to `1`.
            `desired_virtual_count`
                The desired number of virtual shards. Defaults to `128`.
            `actual_virtual_count`
                The actual number of virtual shards. Defaults to `128`.
        """
        return _ShardingConfigCreate(
            virtualPerPhysical=virtual_per_physical,
            desiredCount=desired_count,
            actualCount=actual_count,
            desiredVirtualCount=desired_virtual_count,
            actualVirtualCount=actual_virtual_count,
        )

    @staticmethod
    def vector_index(
        cleanup_interval_seconds: int = 300,
        distance_metric: VectorDistance = VectorDistance.COSINE,
        dynamic_ef_factor: int = 8,
        dynamic_ef_max: int = 500,
        dynamic_ef_min: int = 100,
        ef: int = -1,
        ef_construction: int = 128,
        flat_search_cutoff: int = 40000,
        max_connections: int = 64,
        pq_bit_compression: bool = False,
        pq_centroids: int = 256,
        pq_enabled: bool = False,
        pq_encoder_distribution: PQEncoderDistribution = PQEncoderDistribution.LOG_NORMAL,
        pq_encoder_type: PQEncoderType = PQEncoderType.KMEANS,
        pq_segments: int = 0,
        pq_training_limit: int = 100000,
        skip: bool = False,
        vector_cache_max_objects: int = 1000000000000,
    ) -> _VectorIndexConfigCreate:
        """Create a `_VectorIndexConfigCreate` object to be used when defining the vector index configuration of Weaviate.

        Use this method when defining the `vector_index_config` argument in `collection.create()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for a more detailed view!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigCreate(
            cleanupIntervalSeconds=cleanup_interval_seconds,
            distance=distance_metric,
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            dynamicEfFactor=dynamic_ef_factor,
            efConstruction=ef_construction,
            ef=ef,
            flatSearchCutoff=flat_search_cutoff,
            maxConnections=max_connections,
            pq=_PQConfigCreate(
                bitCompression=pq_bit_compression,
                centroids=pq_centroids,
                enabled=pq_enabled,
                encoder=_PQEncoderConfigCreate(
                    type_=pq_encoder_type,
                    distribution=pq_encoder_distribution,
                ),
                segments=pq_segments,
                trainingLimit=pq_training_limit,
            ),
            skip=skip,
            vectorCacheMaxObjects=vector_cache_max_objects,
        )

    @staticmethod
    def vector_index_type() -> _VectorIndexType:
        """Create a `_VectorIndexType` object to be used when defining the vector index type of Weaviate.

        Use this method when defining the `vector_index_type` argument in `collection.create()`.
        """
        return _VectorIndexType.HNSW


class Reconfigure:
    """Use this factory class to generate the correct `xxxConfig` object for use when using the `collection.update()` method.

    Each staticmethod provides options specific to the named configuration type in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications are caught before the request is sent to Weaviate. Only those configurations that are mutable are
    available in this class. If you wish to update the configuration of an immutable aspect of your collection then you will have to delete
    the collection and re-create it with the new configuration.
    """

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
    def replication(factor: int = 1) -> _ReplicationConfigUpdate:
        """Create a `ReplicationConfigUpdate` object.

        Use this method when defining the `replication_config` argument in `collection.update()`.

        Arguments:
            `factor`
                The replication factor. Defaults to `1`.
        """
        return _ReplicationConfigUpdate(factor=factor)

    @staticmethod
    def vector_index(
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
    ) -> _VectorIndexConfigUpdate:
        """Create a `_VectorIndexConfigUpdate` object.

        Use this method when defining the `vector_index_config` argument in `collection.update()`.

        Arguments:
            See [the docs](https://weaviate.io/developers/weaviate/configuration/indexes#how-to-configure-hnsw) for details!
        """  # noqa: D417 (missing argument descriptions in the docstring)
        return _VectorIndexConfigUpdate(
            dynamicEfFactor=dynamic_ef_factor,
            dynamicEfMin=dynamic_ef_min,
            dynamicEfMax=dynamic_ef_max,
            ef=ef,
            flatSearchCutoff=flat_search_cutoff,
            skip=skip,
            vectorCacheMaxObjects=vector_cache_max_objects,
            pq=_PQConfigUpdate(
                bitCompression=pq_bit_compression,
                centroids=pq_centroids,
                enabled=pq_enabled,
                encoder=_PQEncoderConfigUpdate(
                    type_=pq_encoder_type,
                    distribution=pq_encoder_distribution,
                ),
                segments=pq_segments,
                trainingLimit=pq_training_limit,
            ),
        )

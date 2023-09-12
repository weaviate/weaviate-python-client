from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, cast

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
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


class _ConfigCreateModel(BaseModel):
    model_config = ConfigDict(strict=True)

    def to_dict(self) -> Dict[str, Any]:
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
    type_: PQEncoderType = Field(default=PQEncoderType.KMEANS)
    distribution: PQEncoderDistribution = Field(default=PQEncoderDistribution.LOG_NORMAL)

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["type"] = ret_dict.pop("type_")
        return ret_dict


class _PQEncoderConfigUpdate(_ConfigUpdateModel):
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


class _PQConfigCreate(_ConfigCreateModel):
    bitCompression: bool
    centroids: int
    enabled: bool
    encoder: _PQEncoderConfigCreate
    segments: int
    trainingLimit: int = Field(..., ge=1000000)

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
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


class _VectorizerConfig(_ConfigCreateModel):
    vectorizer: Vectorizer


class PropertyVectorizerConfig(_ConfigCreateModel):
    skip: bool = Field(default=False)
    vectorizePropertyName: bool = Field(default=True, alias="vectorize_property_name")


class GenerativeFactory:
    @classmethod
    def OpenAI(cls) -> _GenerativeConfig:
        return _GenerativeConfig(generative=GenerativeSearches.OPENAI)

    @classmethod
    def Cohere(cls) -> _GenerativeConfig:
        return _GenerativeConfig(generative=GenerativeSearches.COHERE)

    @classmethod
    def Palm(cls) -> _GenerativeConfig:
        return _GenerativeConfig(generative=GenerativeSearches.PALM)


class _Text2VecContextionaryConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_CONTEXTIONARY, frozen=True, exclude=True
    )
    vectorizeClassName: bool


CohereModel = Literal[
    "embed-multilingual-v2.0",
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
    model: Optional[CohereModel]
    truncate: Optional[CohereTruncation]


class _Text2VecHuggingFaceConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(
        default=Vectorizer.TEXT2VEC_HUGGINGFACE, frozen=True, exclude=True
    )
    model: Optional[str]
    passageModel: Optional[str]
    queryModel: Optional[str]
    endpointURL: Optional[str]
    waitForModel: Optional[bool]
    useGPU: Optional[bool]
    useCache: Optional[bool]

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

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        options = {}
        if self.waitForModel is not None:
            options["waitForModel"] = ret_dict.pop("waitForModel")
        if self.useGPU is not None:
            options["useGPU"] = ret_dict.pop("useGPU")
        if self.useCache is not None:
            options["useCache"] = ret_dict.pop("useCache")
        if len(options) > 0:
            ret_dict["options"] = options
        return ret_dict


OpenAIModel = Literal["ada", "babbage", "curie", "davinci"]
OpenAIType = Literal["text", "code"]


class _Text2VecOpenAIConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_OPENAI, frozen=True, exclude=True)
    model: Optional[OpenAIModel]
    modelVersion: Optional[str]
    type_: Optional[OpenAIType]
    vectorizeClassName: bool

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        if self.type_ is not None:
            ret_dict["type"] = ret_dict.pop("type_")
        return ret_dict


class _Text2VecAzureOpenAIConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_OPENAI, frozen=True, exclude=True)
    resourceName: str
    deploymentId: str


class _Text2VecPalmConfig(_VectorizerConfig):
    vectorizer: Vectorizer = Field(default=Vectorizer.TEXT2VEC_PALM, frozen=True, exclude=True)
    projectId: str
    apiEndpoint: Optional[AnyHttpUrl]
    modelId: Optional[str]
    vectorizeClassName: bool

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        if self.apiEndpoint is not None:
            ret_dict["apiEndpoint"] = str(self.apiEndpoint)
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
    name: str
    weight: Optional[float] = Field(default=None, exclude=True)


class _Multi2VecBase(_VectorizerConfig):
    imageFields: Optional[List[Multi2VecField]]
    textFields: Optional[List[Multi2VecField]]
    vectorizeClassName: bool

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
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


class VectorizerFactory:
    """Use this factory class to generate the correct `VectorizerConfig` object for use in the `CollectionConfig` object.

    Each classmethod provides options specific to the named vectorizer in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @classmethod
    def none(cls) -> _VectorizerConfig:
        """Return a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`"""
        return _VectorizerConfig(vectorizer=Vectorizer.NONE)

    @classmethod
    def auto(cls) -> None:
        """Returns a `VectorizerConfig` object with the `Vectorizer` auto-detected from the environment
        variables of the client or Weaviate itself"""
        # TODO: Can this be done?
        pass

    @classmethod
    def img2vec_neural(
        cls,
        image_fields: List[str],
    ) -> _Img2VecNeuralConfig:
        """Returns a `Img2VecNeuralConfig` object for use when vectorizing using the `img2vec-neural` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/img2vec-neural)
        for detailed usage.

        Args:
            `image_fields`: The image fields to use. This is a required field and must match the property fields
            of the collection that are defined as `DataType.BLOB`.

        Returns:
            A `Img2VecNeuralConfig` object.

        Raises:
            `pydantic.ValidationError` if `image_fields` is not a `list`.
        """
        return _Img2VecNeuralConfig(imageFields=image_fields)

    @classmethod
    def multi2vec_clip(
        cls,
        image_fields: Optional[List[Multi2VecField]] = None,
        text_fields: Optional[List[Multi2VecField]] = None,
        vectorize_class_name: bool = True,
    ) -> _Multi2VecClipConfig:
        """Returns a `Multi2VecClipConfig` object for use when vectorizing using the `multi2vec-clip` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-clip)
        for detailed usage.

        Args:
            `image_fields`: The image fields to use in vectorization.
            `text_fields`: The text fields to use in vectorization.
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Multi2VecClipConfig` object.

        Raises:
            `pydantic.ValidationError` if `image_fields` or `text_fields` are not `None` or a `list`.
        """
        return _Multi2VecClipConfig(
            imageFields=image_fields,
            textFields=text_fields,
            vectorizeClassName=vectorize_class_name,
        )

    @classmethod
    def multi2vec_bind(
        cls,
        audio_fields: Optional[List[Multi2VecField]] = None,
        depth_fields: Optional[List[Multi2VecField]] = None,
        image_fields: Optional[List[Multi2VecField]] = None,
        imu_fields: Optional[List[Multi2VecField]] = None,
        text_fields: Optional[List[Multi2VecField]] = None,
        thermal_fields: Optional[List[Multi2VecField]] = None,
        video_fields: Optional[List[Multi2VecField]] = None,
        vectorize_class_name: bool = True,
    ) -> _Multi2VecBindConfig:
        """Returns a `Multi2VecClipConfig` object for use when vectorizing using the `multi2vec-clip` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/multi2vec-bind)
        for detailed usage.

        Args:
            `audio_fields`: The audio fields to use in vectorization.
            `depth_fields`: The depth fields to use in vectorization.
            `image_fields`: The image fields to use in vectorization.
            `imu_fields`: The IMU fields to use in vectorization.
            `text_fields`: The text fields to use in vectorization.
            `thermal_fields`: The thermal fields to use in vectorization.
            `video_fields`: The video fields to use in vectorization.
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Multi2VecClipConfig` object.

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

    @classmethod
    def ref2vec_centroid(
        cls,
        reference_properties: List[str],
        method: Literal["mean"] = "mean",
    ) -> _Ref2VecCentroidConfig:
        """Returns a `Ref2VecCentroidConfig` object for use when vectorizing using the `ref2vec-centroid` model.
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/ref2vec-centroid)
        for detailed usage.

        Args:
            `reference_properties`: The reference properties to use in vectorization.
            `method`: The method to use in vectorization. Defaults to `mean`.

        Returns:
            A `Ref2VecCentroidConfig` object.

        Raises:
            `pydantic.ValidationError` if `reference_properties` is not a `list`.
        """
        return _Ref2VecCentroidConfig(
            referenceProperties=reference_properties,
            method=method,
        )

    @classmethod
    def text2vec_azure_openai(
        cls, resource_name: str, deployment_id: str
    ) -> _Text2VecAzureOpenAIConfig:
        """Returns a `Text2VecAzureOpenAIConfig` object for use when vectorizing using the `text2vec-azure-openai` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-azure-openai)
        for detailed usage.

        Args:
            `resource_name`: The resource name to use.
            `deployment_id`: The deployment ID to use.
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Text2VecAzureOpenAIConfig` object.

        Raises:
            `pydantic.ValidationError` if `resource_name` or `deployment_id` are not `str`.
        """
        return _Text2VecAzureOpenAIConfig(resourceName=resource_name, deploymentId=deployment_id)

    @classmethod
    def text2vec_contextionary(
        cls, vectorize_class_name: bool = True
    ) -> _Text2VecContextionaryConfig:
        """Returns a `Text2VecContextionaryConfig` object for use when vectorizing using the `text2vec-contextionary` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-contextionary)
        for detailed usage.

        Args:
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Text2VecContextionaryConfig` object.

        Raises:
            `pydantic.ValidationError` if `vectorize_class_name` is not a `bool`.
        """
        return _Text2VecContextionaryConfig(vectorizeClassName=vectorize_class_name)

    @classmethod
    def text2vec_cohere(
        cls,
        model: Optional[CohereModel] = None,
        truncate: Optional[CohereTruncation] = None,
    ) -> _Text2VecCohereConfig:
        """Returns a `Text2VecCohereConfig` object for use when vectorizing using the `text2vec-cohere` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-cohere)
        for detailed usage.

        Args:
            `model`: The model to use. Defaults to `None`. If `None`, the default model is used.
            `truncate`: The truncation strategy to use. Defaults to `None`. If `None`, the default truncation strategy is used.

        Returns:
            A `Text2VecCohereConfig` object.

        Raises:
            `pydantic.ValidationError` if `model` or `truncate` are not valid values from the `CohereModel` and `CohereTruncate` types.
        """
        return _Text2VecCohereConfig(model=model, truncate=truncate)

    @classmethod
    def text2vec_gpt4all(
        cls,
        vectorize_class_name: bool = True,
    ) -> _Text2VecGPT4AllConfig:
        """Returns a `Text2VecGPT4AllConfig` object for use when vectorizing using the `text2vec-gpt4all` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Args:
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Text2VecGPT4AllConfig` object.

        Raises:
            `pydantic.ValidationError` if `vectorize_class_name` is not a `bool`.
        """
        return _Text2VecGPT4AllConfig(vectorizeClassName=vectorize_class_name)

    @classmethod
    def text2vec_huggingface(
        cls,
        model: Optional[str] = None,
        passage_model: Optional[str] = None,
        query_model: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        wait_for_model: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        use_cache: Optional[bool] = None,
    ) -> _Text2VecHuggingFaceConfig:
        """Returns a `Text2VecHuggingFaceConfig` object for use when vectorizing using the `text2vec-huggingface` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface)
        for detailed usage.

        Args:
            `model`: The model to use. Defaults to `None`.
            `passage_model`: The passage model to use. Defaults to `None`.
            `query_model`: The query model to use. Defaults to `None`.
            `endpoint_url`: The endpoint URL to use. Defaults to `None`.
            `wait_for_model`: Whether to wait for the model to be loaded. Defaults to `None`.
            `use_gpu`: Whether to use the GPU. Defaults to `None`.
            `use_cache`: Whether to use the cache. Defaults to `None`.

        Returns:
            A `Text2VecHuggingFaceConfig` object.

        Raises:
            `pydantic.ValidationError` if the arguments passed to the function are invalid. It is important to note that some of these variables
            are mutually exclusive. See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface)
            for more details.
        """
        return _Text2VecHuggingFaceConfig(
            model=model,
            passageModel=passage_model,
            queryModel=query_model,
            endpointURL=endpoint_url,
            waitForModel=wait_for_model,
            useGPU=use_gpu,
            useCache=use_cache,
        )

    @classmethod
    def text2vec_openai(
        cls,
        model: Optional[OpenAIModel] = None,
        model_version: Optional[str] = None,
        type_: Optional[OpenAIType] = None,
        vectorize_class_name: bool = True,
    ) -> _Text2VecOpenAIConfig:
        """Returns a `Text2VecOpenAIConfig` object for use when vectorizing using the `text2vec-openai` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-openai)
        for detailed usage.

        Args:
            `model`: The model to use. Defaults to `None`. If `None`, the default model is used.
            `model_version`: The model version to use. Defaults to `None`.
            `type_`: The type of model to use. Defaults to `None`. If `None`, the default type is used.
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Text2VecOpenAIConfig` object.

        Raises:
            `pydantic.ValidationError` if `model` or `type_` are not valid values from the `OpenAIModel` and `OpenAIType` types.
        """
        return _Text2VecOpenAIConfig(
            model=model,
            modelVersion=model_version,
            type_=type_,
            vectorizeClassName=vectorize_class_name,
        )

    @classmethod
    def text2vec_palm(
        cls,
        project_id: str,
        api_endpoint: Optional[AnyHttpUrl] = None,
        model_id: Optional[str] = None,
        vectorize_class_name: bool = True,
    ) -> _Text2VecPalmConfig:
        """Returns a `Text2VecPalmConfig` object for use when vectorizing using the `text2vec-palm` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-palm)
        for detailed usage.

        Args:
            `project_id`: The project ID to use.
            `api_endpoint`: The API endpoint to use. Defaults to `None`.
            `model_id`: The model ID to use. Defaults to `None`.
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Text2VecPalmConfig` object.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        return _Text2VecPalmConfig(
            projectId=project_id,
            apiEndpoint=api_endpoint,
            modelId=model_id,
            vectorizeClassName=vectorize_class_name,
        )

    @classmethod
    def text2vec_transformers(
        cls,
        pooling_strategy: Literal["masked_mean", "cls"] = "masked_mean",
        vectorize_class_name: bool = True,
    ) -> _Text2VecTransformersConfig:
        """Returns a `Text2VecTransformersConfig` object for use when vectorizing using the `text2vec-transformers` model
        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-transformers)
        for detailed usage.

        Args:
            `pooling_strategy`: The pooling strategy to use. Defaults to `masked_mean`.
            `vectorize_class_name`: Whether to vectorize the class name. Defaults to `True`.

        Returns:
            A `Text2VecTransformersConfig` object.

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
    vectorIndexType: VectorIndexType = Field(
        default=VectorIndexType.HNSW, alias="vector_index_type"
    )
    moduleConfig: _VectorizerConfig = Field(
        default=VectorizerFactory.none(), alias="vectorizer_config"
    )
    generativeSearch: Optional[_GenerativeConfig] = Field(default=None, alias="generative_search")

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
            elif isinstance(val, _GenerativeConfig):
                self.__add_to_module_config(ret_dict, val.generative.value, {})
            elif isinstance(val, _VectorizerConfig):
                ret_dict["vectorizer"] = val.vectorizer.value
                if val.vectorizer != Vectorizer.NONE:
                    self.__add_to_module_config(ret_dict, val.vectorizer.value, val.to_dict())
            else:
                assert isinstance(val, _ConfigCreateModel)
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
    vectorizer_config: Optional[_VectorizerConfig] = None

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


class Property(_ConfigCreateModel):
    name: str
    dataType: DataType = Field(default=..., alias="data_type")
    indexFilterable: Optional[bool] = Field(default=None, alias="index_filterable")
    indexSearchable: Optional[bool] = Field(default=None, alias="index_searchable")
    description: Optional[str] = Field(default=None)
    moduleConfig: Optional[PropertyVectorizerConfig] = Field(
        default=None, alias="vectorizer_config"
    )
    tokenization: Optional[Tokenization] = Field(default=None)

    def to_dict(self, vectorizer: Optional[Vectorizer] = None) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        if "moduleConfig" in ret_dict and vectorizer is not None:
            ret_dict["moduleConfig"] = {vectorizer.value: ret_dict["moduleConfig"]}
        return ret_dict


class ReferencePropertyBase(_ConfigCreateModel):
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


class _CollectionConfigCreate(_CollectionConfigCreateBase):
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


class ConfigFactory:
    """Use this factory class to generate the correct `xxxConfig` object for use in the `CollectionConfig` object for each type of
    Weaviate configuration that you'd like to specify. E.g., `.multi_tenancy()` will return a `MultiTenancyConfigCreate` object
    to be used in the `multi_tenancy_config` attribute of `CollectionConfig`.

    Each classmethod provides options specific to the named configuration type in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications are caught before the request is sent to Weaviate.
    """

    @classmethod
    def inverted_index(
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
    ) -> _InvertedIndexConfigCreate:
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

    @classmethod
    def multi_tenancy(cls, enabled: bool = False) -> _MultiTenancyConfigCreate:
        return _MultiTenancyConfigCreate(enabled=enabled)

    @classmethod
    def replication(cls, factor: int = 1) -> _ReplicationConfigCreate:
        """Create a `ReplicationConfigCreate` object to be used when defining the replication configuration of Weaviate.

        Args:
            `factor`: The replication factor. Defaults to `1`.

        Returns:
            A `ReplicationConfigCreate` object.
        """
        return _ReplicationConfigCreate(factor=factor)

    @classmethod
    def sharding(
        cls,
        virtual_per_physical: int = 128,
        desired_count: int = 1,
        actual_count: int = 1,
        desired_virtual_count: int = 128,
        actual_virtual_count: int = 128,
    ) -> _ShardingConfigCreate:
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
        return _ShardingConfigCreate(
            virtualPerPhysical=virtual_per_physical,
            desiredCount=desired_count,
            actualCount=actual_count,
            desiredVirtualCount=desired_virtual_count,
            actualVirtualCount=actual_virtual_count,
        )

    @classmethod
    def vector_index(
        cls,
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


class ConfigUpdateFactory:
    @classmethod
    def inverted_index(
        cls,
        bm25_b: Optional[float] = None,
        bm25_k1: Optional[float] = None,
        cleanup_interval_seconds: Optional[int] = None,
        stopwords_additions: Optional[List[str]] = None,
        stopwords_preset: Optional[StopwordsPreset] = None,
        stopwords_removals: Optional[List[str]] = None,
    ) -> _InvertedIndexConfigUpdate:
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
        return _InvertedIndexConfigUpdate(
            bm25=_BM25ConfigUpdate(b=bm25_b, k1=bm25_k1),
            cleanupIntervalSeconds=cleanup_interval_seconds,
            stopwords=_StopwordsUpdate(
                preset=stopwords_preset,
                additions=stopwords_additions,
                removals=stopwords_removals,
            ),
        )

    @classmethod
    def replication(cls, factor: int = 1) -> _ReplicationConfigUpdate:
        """Create a `ReplicationConfigUpdate` object.

        Args:
            `factor`: The replication factor. Defaults to `1`.

        Returns:
            A `ReplicationConfigUpdate` object.
        """
        return _ReplicationConfigUpdate(factor=factor)

    @classmethod
    def vector_index(
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
    ) -> _VectorIndexConfigUpdate:
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

import warnings
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union, cast

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator
from typing_extensions import TypeAlias, deprecated

from weaviate.collections.classes.config_base import _ConfigCreateModel, _EnumLikeStr
from ...warnings import _Warnings

# See https://docs.cohere.com/docs/cohere-embed for reference
CohereModel: TypeAlias = Literal[
    "embed-multilingual-v2.0",
    "embed-multilingual-v3.0",
    "embed-multilingual-light-v3.0",
    "small",
    "medium",
    "large",
    "multilingual-22-12",
    "embed-english-v2.0",
    "embed-english-light-v2.0",
    "embed-english-v3.0",
    "embed-english-light-v3.0",
]
CohereMultimodalModel: TypeAlias = Literal[
    "embed-multilingual-v3.0",
    "embed-multilingual-light-v3.0",
    "embed-english-v3.0",
    "embed-english-light-v3.0",
]
CohereTruncation: TypeAlias = Literal["NONE", "START", "END", "LEFT", "RIGHT"]
OpenAIModel: TypeAlias = Literal[
    "text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"
]
JinaModel: TypeAlias = Literal[
    "jina-embeddings-v2-base-en",
    "jina-embeddings-v2-small-en",
    "jina-embeddings-v2-base-zh",
    "jina-embeddings-v2-base-es",
    "jina-embeddings-v2-base-code",
    "jina-embeddings-v3",
]
JinaMultimodalModel: TypeAlias = Literal[
    "jina-clip-v1",
    "jina-clip-v2",
]
VoyageModel: TypeAlias = Literal[
    "voyage-3",
    "voyage-3-lite",
    "voyage-large-2",
    "voyage-code-2",
    "voyage-2",
    "voyage-law-2",
    "voyage-large-2-instruct",
    "voyage-finance-2",
    "voyage-multilingual-2",
]
VoyageMultimodalModel: TypeAlias = Literal["voyage-multimodal-3",]
AWSModel: TypeAlias = Literal[
    "amazon.titan-embed-text-v1",
    "cohere.embed-english-v3",
    "cohere.embed-multilingual-v3",
]
AWSService: TypeAlias = Literal[
    "bedrock",
    "sagemaker",
]
WeaviateModel: TypeAlias = Literal["Snowflake/snowflake-arctic-embed-m-v1.5"]


class Vectorizers(str, Enum):
    """The available vectorization modules in Weaviate.

    These modules encode binary data into lists of floats called vectors.
    See the [docs](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules) for more details.

    Attributes:
        `NONE`
            No vectorizer.
        `TEXT2VEC_AWS`
            Weaviate module backed by AWS text-based embedding models.
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
        `TEXT2VEC_JINAAI`
            Weaviate module backed by Jina AI text-based embedding models.
        `TEXT2VEC_VOYAGEAI`
            Weaviate module backed by Voyage AI text-based embedding models.
        `TEXT2VEC_WEAVIATE`
            Weaviate module backed by Weaviate's self-hosted text-based embedding models.
        `IMG2VEC_NEURAL`
            Weaviate module backed by a ResNet-50 neural network for images.
        `MULTI2VEC_CLIP`
            Weaviate module backed by a Sentence-BERT CLIP model for images and text.
        `MULTI2VEC_PALM`
            Weaviate module backed by a palm model for images and text.
        `MULTI2VEC_BIND`
            Weaviate module backed by the ImageBind model for images, text, audio, depth, IMU, thermal, and video.
        `MULTI2VEC_VOYAGEAI`
            Weaviate module backed by a Voyage AI multimodal embedding models.
        `REF2VEC_CENTROID`
            Weaviate module backed by a centroid-based model that calculates an object's vectors from its referenced vectors.
    """

    NONE = "none"
    TEXT2VEC_AWS = "text2vec-aws"
    TEXT2VEC_COHERE = "text2vec-cohere"
    TEXT2VEC_CONTEXTIONARY = "text2vec-contextionary"
    TEXT2VEC_DATABRICKS = "text2vec-databricks"
    TEXT2VEC_GPT4ALL = "text2vec-gpt4all"
    TEXT2VEC_HUGGINGFACE = "text2vec-huggingface"
    TEXT2VEC_MISTRAL = "text2vec-mistral"
    TEXT2VEC_OLLAMA = "text2vec-ollama"
    TEXT2VEC_OPENAI = "text2vec-openai"
    TEXT2VEC_PALM = "text2vec-palm"  # change to google once 1.27 is the lowest supported version
    TEXT2VEC_TRANSFORMERS = "text2vec-transformers"
    TEXT2VEC_JINAAI = "text2vec-jinaai"
    TEXT2VEC_VOYAGEAI = "text2vec-voyageai"
    TEXT2VEC_WEAVIATE = "text2vec-weaviate"
    IMG2VEC_NEURAL = "img2vec-neural"
    MULTI2VEC_CLIP = "multi2vec-clip"
    MULTI2VEC_COHERE = "multi2vec-cohere"
    MULTI2VEC_JINAAI = "multi2vec-jinaai"
    MULTI2VEC_BIND = "multi2vec-bind"
    MULTI2VEC_PALM = "multi2vec-palm"  # change to google once 1.27 is the lowest supported version
    MULTI2VEC_VOYAGEAI = "multi2vec-voyageai"
    REF2VEC_CENTROID = "ref2vec-centroid"


class VectorDistances(str, Enum):
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


class _VectorizerConfigCreate(_ConfigCreateModel):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(default=..., exclude=True)


class _Text2VecContextionaryConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_CONTEXTIONARY, frozen=True, exclude=True
    )
    vectorizeClassName: bool


class _VectorizerCustomConfig(_VectorizerConfigCreate):
    module_config: Optional[Dict[str, Any]]

    def _to_dict(self) -> Dict[str, Any]:
        if self.module_config is None:
            return {}
        return self.module_config


class _Text2VecAWSConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_AWS, frozen=True, exclude=True
    )
    model: Optional[str]
    endpoint: Optional[str]
    region: str
    service: str
    vectorizeClassName: bool

    @field_validator("region")
    def _check_name(cls, r: str) -> str:
        if r == "":
            raise ValueError("region is a required argument and must be given")
        return r


class _Text2VecAzureOpenAIConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_OPENAI, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    resourceName: str
    deploymentId: str
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Text2VecHuggingFaceConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_HUGGINGFACE, frozen=True, exclude=True
    )
    model: Optional[str]
    passageModel: Optional[str]
    queryModel: Optional[str]
    endpointURL: Optional[AnyHttpUrl]
    waitForModel: Optional[bool]
    useGPU: Optional[bool]
    useCache: Optional[bool]
    vectorizeClassName: bool

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


class _Text2VecMistralConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_MISTRAL, frozen=True, exclude=True
    )
    model: Optional[str]
    vectorizeClassName: bool


class _Text2VecDatabricksConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_DATABRICKS, frozen=True, exclude=True
    )
    endpoint: str
    instruction: Optional[str]
    vectorizeClassName: bool


OpenAIType = Literal["text", "code"]


class _Text2VecOpenAIConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_OPENAI, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    dimensions: Optional[int]
    model: Optional[str]
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


class _Text2VecCohereConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_COHERE, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    model: Optional[str]
    truncate: Optional[CohereTruncation]
    vectorizeClassName: bool

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Text2VecGoogleConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_PALM, frozen=True, exclude=True
    )
    projectId: str
    apiEndpoint: Optional[str]
    modelId: Optional[str]
    vectorizeClassName: bool
    titleProperty: Optional[str]


class _Text2VecTransformersConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_TRANSFORMERS, frozen=True, exclude=True
    )
    poolingStrategy: Literal["masked_mean", "cls"]
    vectorizeClassName: bool
    inferenceUrl: Optional[str]
    passageInferenceUrl: Optional[str]
    queryInferenceUrl: Optional[str]


class _Text2VecGPT4AllConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_GPT4ALL, frozen=True, exclude=True
    )
    vectorizeClassName: bool


class _Text2VecJinaConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_JINAAI, frozen=True, exclude=True
    )
    baseURL: Optional[str]
    dimensions: Optional[int]
    model: Optional[str]
    vectorizeClassName: bool


class _Text2VecVoyageConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_VOYAGEAI, frozen=True, exclude=True
    )
    model: Optional[str]
    baseURL: Optional[str]
    truncate: Optional[bool]
    vectorizeClassName: bool


class _Text2VecWeaviateConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_WEAVIATE, frozen=True, exclude=True
    )
    model: Optional[str]
    baseURL: Optional[str]
    vectorizeClassName: bool
    dimensions: Optional[int]


class _Text2VecOllamaConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.TEXT2VEC_OLLAMA, frozen=True, exclude=True
    )
    model: Optional[str]
    apiEndpoint: Optional[str]
    vectorizeClassName: bool


class _Img2VecNeuralConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.IMG2VEC_NEURAL, frozen=True, exclude=True
    )
    imageFields: List[str]


class Multi2VecField(BaseModel):
    """Use this class when defining the fields to use in the `Multi2VecClip` and `Multi2VecBind` vectorizers."""

    name: str
    weight: Optional[float] = Field(default=None, exclude=True)


class _Multi2VecBase(_VectorizerConfigCreate):
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


class _Multi2VecCohereConfig(_Multi2VecBase):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.MULTI2VEC_COHERE, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    model: Optional[str]
    truncate: Optional[CohereTruncation]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Multi2VecJinaConfig(_Multi2VecBase):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.MULTI2VEC_JINAAI, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    model: Optional[str]
    dimensions: Optional[int]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Multi2VecClipConfig(_Multi2VecBase):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.MULTI2VEC_CLIP, frozen=True, exclude=True
    )
    inferenceUrl: Optional[str]


class _Multi2VecGoogleConfig(_Multi2VecBase, _VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.MULTI2VEC_PALM, frozen=True, exclude=True
    )
    videoFields: Optional[List[Multi2VecField]]
    projectId: str
    location: Optional[str]
    modelId: Optional[str]
    dimensions: Optional[int]
    videoIntervalSeconds: Optional[int]
    vectorizeClassName: bool


class _Multi2VecBindConfig(_Multi2VecBase):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.MULTI2VEC_BIND, frozen=True, exclude=True
    )
    audioFields: Optional[List[Multi2VecField]]
    depthFields: Optional[List[Multi2VecField]]
    IMUFields: Optional[List[Multi2VecField]]
    thermalFields: Optional[List[Multi2VecField]]
    videoFields: Optional[List[Multi2VecField]]


class _Multi2VecVoyageaiConfig(_Multi2VecBase):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.MULTI2VEC_VOYAGEAI, frozen=True, exclude=True
    )
    baseURL: Optional[AnyHttpUrl]
    model: Optional[str]
    truncation: Optional[bool]
    output_encoding: Optional[str]

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict = super()._to_dict()
        if self.baseURL is not None:
            ret_dict["baseURL"] = self.baseURL.unicode_string()
        return ret_dict


class _Ref2VecCentroidConfig(_VectorizerConfigCreate):
    vectorizer: Union[Vectorizers, _EnumLikeStr] = Field(
        default=Vectorizers.REF2VEC_CENTROID, frozen=True, exclude=True
    )
    referenceProperties: List[str]
    method: Literal["mean"]


def _map_multi2vec_fields(
    fields: Optional[Union[List[str], List[Multi2VecField]]]
) -> Optional[List[Multi2VecField]]:
    if fields is None:
        return None
    return [Multi2VecField(name=field) if isinstance(field, str) else field for field in fields]


class _Vectorizer:
    """Use this factory class to create the correct object for the `vectorizer_config` argument in the `collections.create()` method.

    Each staticmethod provides options specific to the named vectorizer in the function's name. Under-the-hood data validation steps
    will ensure that any mis-specifications will be caught before the request is sent to Weaviate.
    """

    @staticmethod
    def none() -> _VectorizerConfigCreate:
        """Create a `_VectorizerConfigCreate` object with the vectorizer set to `Vectorizer.NONE`."""
        return _VectorizerConfigCreate(vectorizer=Vectorizers.NONE)

    @staticmethod
    def img2vec_neural(
        image_fields: List[str],
    ) -> _VectorizerConfigCreate:
        """Create a `_Img2VecNeuralConfigCreate` object for use when vectorizing using the `img2vec-neural` model.

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
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        interference_url: Optional[str] = None,
        inference_url: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecClipConfigCreate` object for use when vectorizing using the `multi2vec-clip` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/transformers/embeddings-multimodal)
        for detailed usage.

        Arguments:
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.
            `inference_url`
                The inference url to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `image_fields` or `text_fields` are not `None` or a `list`.
        """
        if interference_url is not None:
            if inference_url is not None:
                raise ValueError(
                    "You have provided `interference_url` as well as `inference_url`. Please only provide `inference_url`, as `interference_url` is deprecated."
                )
            else:
                warnings.warn(
                    message="""This parameter is deprecated and will be removed in a future release. Please use `inference_url` instead.""",
                    category=DeprecationWarning,
                    stacklevel=1,
                )

        return _Multi2VecClipConfig(
            imageFields=_map_multi2vec_fields(image_fields),
            textFields=_map_multi2vec_fields(text_fields),
            vectorizeClassName=vectorize_collection_name,
            inferenceUrl=inference_url,
        )

    @staticmethod
    def multi2vec_bind(
        audio_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        depth_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        imu_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        thermal_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecBindConfigCreate` object for use when vectorizing using the `multi2vec-clip` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/imagebind/embeddings-multimodal)
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
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if any of the `*_fields` are not `None` or a `list`.
        """
        return _Multi2VecBindConfig(
            audioFields=_map_multi2vec_fields(audio_fields),
            depthFields=_map_multi2vec_fields(depth_fields),
            imageFields=_map_multi2vec_fields(image_fields),
            IMUFields=_map_multi2vec_fields(imu_fields),
            textFields=_map_multi2vec_fields(text_fields),
            thermalFields=_map_multi2vec_fields(thermal_fields),
            videoFields=_map_multi2vec_fields(video_fields),
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def ref2vec_centroid(
        reference_properties: List[str],
        method: Literal["mean"] = "mean",
    ) -> _VectorizerConfigCreate:
        """Create a `_Ref2VecCentroidConfigCreate` object for use when vectorizing using the `ref2vec-centroid` model.

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
    def text2vec_aws(
        model: Optional[Union[AWSModel, str]] = None,
        region: str = "",  # cant have a non-default value after a default value, but we cant change the order for BC - will be validated in the model
        endpoint: Optional[str] = None,
        service: Union[AWSService, str] = "bedrock",
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecAWSConfigCreate` object for use when vectorizing using the `text2vec-aws` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/aws/embeddings)
        for detailed usage.

        Arguments:
            `model`
                The model to use, REQUIRED for service "bedrock".
            `region`
                The AWS region to run the model from, REQUIRED.
            `endpoint`
                The model to use, REQUIRED for service "sagemaker".
            `service`
                The AWS service to use, options are "bedrock" and "sagemaker".
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _Text2VecAWSConfig(
            model=model,
            region=region,
            vectorizeClassName=vectorize_collection_name,
            service=service,
            endpoint=endpoint,
        )

    @staticmethod
    def text2vec_azure_openai(
        resource_name: str,
        deployment_id: str,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecAzureOpenAIConfigCreate` object for use when vectorizing using the `text2vec-azure-openai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/openai-azure/embeddings)
        for detailed usage.

        Arguments:
            `resource_name`
                The resource name to use, REQUIRED.
            `deployment_id`
                The deployment ID to use, REQUIRED.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `resource_name` or `deployment_id` are not `str`.
        """
        return _Text2VecAzureOpenAIConfig(
            baseURL=base_url,
            resourceName=resource_name,
            deploymentId=deployment_id,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def text2vec_contextionary(vectorize_collection_name: bool = True) -> _VectorizerConfigCreate:
        """Create a `_Text2VecContextionaryConfigCreate` object for use when vectorizing using the `text2vec-contextionary` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-contextionary)
        for detailed usage.

        Arguments:
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError`` if `vectorize_collection_name` is not a `bool`.
        """
        return _Text2VecContextionaryConfig(vectorizeClassName=vectorize_collection_name)

    @staticmethod
    def custom(
        module_name: str, module_config: Optional[Dict[str, Any]] = None
    ) -> _VectorizerConfigCreate:
        """Create a `_VectorizerCustomConfig` object for use when vectorizing using a custom specification.

        Arguments:
            `module_name`
                The name of the module to use, REQUIRED.
            `module_config`
                The configuration to use for the module. Defaults to `None`, which uses the server-defined default.
        """
        return _VectorizerCustomConfig(
            vectorizer=_EnumLikeStr(module_name), module_config=module_config
        )

    @staticmethod
    def text2vec_cohere(
        model: Optional[Union[CohereModel, str]] = None,
        truncate: Optional[CohereTruncation] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecCohereConfigCreate` object for use when vectorizing using the `text2vec-cohere` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/cohere/embeddings)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `truncate`
                The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `model` is not a valid value from the `CohereModel` type or if `truncate` is not a valid value from the `CohereTruncation` type.
        """
        return _Text2VecCohereConfig(
            baseURL=base_url,
            model=model,
            truncate=truncate,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def multi2vec_cohere(
        *,
        model: Optional[Union[CohereMultimodalModel, str]] = None,
        truncate: Optional[CohereTruncation] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecCohereConfig` object for use when vectorizing using the `multi2vec-cohere` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/cohere/embeddings-multimodal)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `truncate`
                The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.

        Raises:
            `pydantic.ValidationError` if `model` is not a valid value from the `CohereMultimodalModel` type or if `truncate` is not a valid value from the `CohereTruncation` type.
        """
        return _Multi2VecCohereConfig(
            baseURL=base_url,
            model=model,
            truncate=truncate,
            vectorizeClassName=vectorize_collection_name,
            imageFields=_map_multi2vec_fields(image_fields),
            textFields=_map_multi2vec_fields(text_fields),
        )

    @staticmethod
    def multi2vec_voyageai(
        *,
        model: Optional[Union[CohereMultimodalModel, str]] = None,
        truncation: Optional[bool] = None,
        output_encoding: Optional[str],
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecCohereConfig` object for use when vectorizing using the `multi2vec-cohere` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/cohere/embeddings-multimodal)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `truncate`
                The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            `output_encoding`
                Format in which the embeddings are encoded. Defaults to `None`, so the embeddings are represented as a list of floating-point numbers.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.

        Raises:
            `pydantic.ValidationError` if `model` is not a valid value from the `CohereMultimodalModel` type or if `truncate` is not a valid value from the `CohereTruncation` type.
        """
        return _Multi2VecVoyageaiConfig(
            baseURL=base_url,
            model=model,
            truncation=truncation,
            output_encoding=output_encoding,
            vectorizeClassName=vectorize_collection_name,
            imageFields=_map_multi2vec_fields(image_fields),
            textFields=_map_multi2vec_fields(text_fields),
        )

    @staticmethod
    def text2vec_databricks(
        *,
        endpoint: str,
        instruction: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecDatabricksConfig` object for use when vectorizing using the `text2vec-databricks` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/databricks/embeddings)
        for detailed usage.

        Arguments:
            `endpoint`
                The endpoint to use.
            `instruction`
                The instruction strategy to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `truncate` is not a valid value from the `CohereModel` type.
        """
        return _Text2VecDatabricksConfig(
            endpoint=endpoint,
            instruction=instruction,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def text2vec_gpt4all(
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecGPT4AllConfigCreate` object for use when vectorizing using the `text2vec-gpt4all` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/gpt4all/embeddings)
        for detailed usage.

        Arguments:
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `vectorize_collection_name` is not a `bool`.
        """
        return _Text2VecGPT4AllConfig(vectorizeClassName=vectorize_collection_name)

    @staticmethod
    def text2vec_huggingface(
        model: Optional[str] = None,
        passage_model: Optional[str] = None,
        query_model: Optional[str] = None,
        endpoint_url: Optional[AnyHttpUrl] = None,
        wait_for_model: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecHuggingFaceConfigCreate` object for use when vectorizing using the `text2vec-huggingface` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/huggingface/embeddings)
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
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if the arguments passed to the function are invalid.
                It is important to note that some of these variables are mutually exclusive.
                    See the [documentation](https://weaviate.io/developers/weaviate/model-providers/huggingface/embeddings#vectorizer-parameters) for more details.
        """
        return _Text2VecHuggingFaceConfig(
            model=model,
            passageModel=passage_model,
            queryModel=query_model,
            endpointURL=endpoint_url,
            waitForModel=wait_for_model,
            useGPU=use_gpu,
            useCache=use_cache,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def text2vec_mistral(
        *,
        model: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecMistralConfig` object for use when vectorizing using the `text2vec-mistral` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/mistral/embeddings)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _Text2VecMistralConfig(model=model, vectorizeClassName=vectorize_collection_name)

    @staticmethod
    def text2vec_ollama(
        *,
        api_endpoint: Optional[str] = None,
        model: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecOllamaConfig` object for use when vectorizing using the `text2vec-ollama` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/ollama/embeddings)
        for detailed usage.

        Arguments:
            `api_endpoint`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
                Docker users may need to specify an alias, such as `http://host.docker.internal:11434` so that the container can access the host machine.
            `modelId`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _Text2VecOllamaConfig(
            apiEndpoint=api_endpoint,
            model=model,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def text2vec_openai(
        model: Optional[Union[OpenAIModel, str]] = None,
        model_version: Optional[str] = None,
        type_: Optional[OpenAIType] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
        dimensions: Optional[int] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecOpenAIConfigCreate` object for use when vectorizing using the `text2vec-openai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/openai/embeddings)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `model_version`
                The model version to use. Defaults to `None`, which uses the server-defined default.
            `type_`
                The type of model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `dimensions`
                Number of dimensions. Applicable to v3 OpenAI models only. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `type_` is not a valid value from the `OpenAIType` type.
        """
        return _Text2VecOpenAIConfig(
            baseURL=base_url,
            model=model,
            modelVersion=model_version,
            type_=type_,
            vectorizeClassName=vectorize_collection_name,
            dimensions=dimensions,
        )

    @staticmethod
    @deprecated(
        "This method is deprecated and will be removed in Q2 25. Please use `text2vec_google` instead."
    )
    def text2vec_palm(
        project_id: str,
        api_endpoint: Optional[str] = None,
        model_id: Optional[str] = None,
        title_property: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecGoogleConfig` object for use when vectorizing using the `text2vec-palm` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/embeddings)
        for detailed usage.

        Arguments:
            `project_id`
                The project ID to use, REQUIRED.
            `api_endpoint`
                The API endpoint to use without a leading scheme such as `http://`. Defaults to `None`, which uses the server-defined default
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `title_property`
                The Weaviate property name for the `gecko-002` or `gecko-003` model to use as the title.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        _Warnings.palm_to_google_t2v()
        return _Text2VecGoogleConfig(
            projectId=project_id,
            apiEndpoint=api_endpoint,
            modelId=model_id,
            vectorizeClassName=vectorize_collection_name,
            titleProperty=title_property,
        )

    @staticmethod
    def text2vec_google(
        project_id: str,
        api_endpoint: Optional[str] = None,
        model_id: Optional[str] = None,
        title_property: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecGoogleConfig` object for use when vectorizing using the `text2vec-google` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/embeddings)
        for detailed usage.

        Arguments:
            `project_id`
                The project ID to use, REQUIRED.
            `api_endpoint`
                The API endpoint to use without a leading scheme such as `http://`. Defaults to `None`, which uses the server-defined default
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `title_property`
                The Weaviate property name for the `gecko-002` or `gecko-003` model to use as the title.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        return _Text2VecGoogleConfig(
            projectId=project_id,
            apiEndpoint=api_endpoint,
            modelId=model_id,
            vectorizeClassName=vectorize_collection_name,
            titleProperty=title_property,
        )

    @staticmethod
    @deprecated(
        "This method is deprecated and will be removed in Q2 25. Please use `multi2vec_google` instead."
    )
    def multi2vec_palm(
        *,
        location: str,
        project_id: str,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        dimensions: Optional[int] = None,
        model_id: Optional[str] = None,
        video_interval_seconds: Optional[int] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecPalmConfig` object for use when vectorizing using the `text2vec-palm` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/embeddings-multimodal)
        for detailed usage.

        Arguments:
            `location`
                Where the model runs. REQUIRED.
            `project_id`
                The project ID to use, REQUIRED.
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.
            `video_fields`
                The video fields to use in vectorization.
            `dimensions`
                The number of dimensions to use. Defaults to `None`, which uses the server-defined default.
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `video_interval_seconds`
                Length of a video interval. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        _Warnings.palm_to_google_m2v()
        return _Multi2VecGoogleConfig(
            projectId=project_id,
            location=location,
            imageFields=_map_multi2vec_fields(image_fields),
            textFields=_map_multi2vec_fields(text_fields),
            videoFields=_map_multi2vec_fields(video_fields),
            dimensions=dimensions,
            modelId=model_id,
            videoIntervalSeconds=video_interval_seconds,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def multi2vec_google(
        *,
        location: str,
        project_id: str,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        dimensions: Optional[int] = None,
        model_id: Optional[str] = None,
        video_interval_seconds: Optional[int] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecGoogleConfig` object for use when vectorizing using the `text2vec-google` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/embeddings-multimodal)
        for detailed usage.

        Arguments:
            `location`
                Where the model runs. REQUIRED.
            `project_id`
                The project ID to use, REQUIRED.
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.
            `video_fields`
                The video fields to use in vectorization.
            `dimensions`
                The number of dimensions to use. Defaults to `None`, which uses the server-defined default.
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `video_interval_seconds`
                Length of a video interval. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        return _Multi2VecGoogleConfig(
            projectId=project_id,
            location=location,
            imageFields=_map_multi2vec_fields(image_fields),
            textFields=_map_multi2vec_fields(text_fields),
            videoFields=_map_multi2vec_fields(video_fields),
            dimensions=dimensions,
            modelId=model_id,
            videoIntervalSeconds=video_interval_seconds,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def text2vec_transformers(
        pooling_strategy: Literal["masked_mean", "cls"] = "masked_mean",
        vectorize_collection_name: bool = True,
        inference_url: Optional[str] = None,
        passage_inference_url: Optional[str] = None,
        query_inference_url: Optional[str] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecTransformersConfigCreate` object for use when vectorizing using the `text2vec-transformers` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/transformers/embeddings)
        for detailed usage.

        Arguments:
            `pooling_strategy`
                The pooling strategy to use. Defaults to `masked_mean`.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `inference_url`
                The inference url to use where API requests should go. You can use either this OR passage/query_inference_url. Defaults to `None`, which uses the server-defined default.
            `passage_inference_url`
                The inference url to use where passage API requests should go. You can use either this and query_inference_url OR inference_url. Defaults to `None`, which uses the server-defined default.
            `query_inference_url`
                The inference url to use where query API requests should go. You can use either this and passage_inference_url OR inference_url. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `pooling_strategy` is not a valid value from the `PoolingStrategy` type.
        """
        return _Text2VecTransformersConfig(
            poolingStrategy=pooling_strategy,
            vectorizeClassName=vectorize_collection_name,
            inferenceUrl=inference_url,
            passageInferenceUrl=passage_inference_url,
            queryInferenceUrl=query_inference_url,
        )

    @staticmethod
    def text2vec_jinaai(
        model: Optional[Union[JinaModel, str]] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecJinaConfigCreate` object for use when vectorizing using the `text2vec-jinaai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/embeddings)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/embeddings#available-models) for more details.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to send the vectorization requests to. Defaults to `None`, which uses the server-defined default.
            `dimensions`
                The number of dimensions for the generated embeddings. Defaults to `None`, which uses the server-defined default.
        """
        return _Text2VecJinaConfig(
            model=model,
            vectorizeClassName=vectorize_collection_name,
            baseURL=base_url,
            dimensions=dimensions,
        )

    @staticmethod
    def multi2vec_jinaai(
        *,
        model: Optional[Union[JinaMultimodalModel, str]] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
        dimensions: Optional[int] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
    ) -> _VectorizerConfigCreate:
        """Create a `_Multi2VecJinaConfig` object for use when vectorizing using the `multi2vec-jinaai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/embeddings-multimodal)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `dimensions`
                The number of dimensions for the generated embeddings (only available for some models). Defaults to `None`, which uses the server-defined default.
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.

        Raises:
            `pydantic.ValidationError` if `model` is not a valid value from the `JinaMultimodalModel` type.
        """
        return _Multi2VecJinaConfig(
            baseURL=base_url,
            model=model,
            dimensions=dimensions,
            vectorizeClassName=vectorize_collection_name,
            imageFields=_map_multi2vec_fields(image_fields),
            textFields=_map_multi2vec_fields(text_fields),
        )

    @staticmethod
    def text2vec_voyageai(
        *,
        model: Optional[Union[VoyageModel, str]] = None,
        base_url: Optional[str] = None,
        truncate: Optional[bool] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorizerConfigCreate:
        """Create a `_Text2VecVoyageConfigCreate` object for use when vectorizing using the `text2vec-voyageai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/voyageai/embeddings)
        for detailed usage.

        Arguments:
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/model-providers/voyageai/embeddings#available-models) for more details.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `truncate`
                Whether to truncate the input texts to fit within the context length. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _Text2VecVoyageConfig(
            model=model,
            baseURL=base_url,
            truncate=truncate,
            vectorizeClassName=vectorize_collection_name,
        )

    @staticmethod
    def text2vec_weaviate(
        *,
        model: Optional[Union[WeaviateModel, str]] = None,
        base_url: Optional[str] = None,
        vectorize_collection_name: bool = True,
        dimensions: Optional[int] = None,
    ) -> _VectorizerConfigCreate:
        """TODO: add docstrings when the documentation is available."""
        return _Text2VecWeaviateConfig(
            model=model,
            baseURL=base_url,
            vectorizeClassName=vectorize_collection_name,
            dimensions=dimensions,
        )

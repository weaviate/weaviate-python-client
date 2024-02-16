from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import AnyHttpUrl, Field
from weaviate.collections.classes.config_vectorizers import (
    _ConfigCreateModel,
    _Img2VecNeuralConfig,
    _Multi2VecBindConfig,
    _Multi2VecClipConfig,
    _Ref2VecCentroidConfig,
    _Text2VecAWSConfig,
    _Text2VecAzureOpenAIConfig,
    _Text2VecCohereConfig,
    _Text2VecContextionaryConfig,
    _Text2VecGPT4AllConfig,
    _Text2VecHuggingFaceConfig,
    _Text2VecJinaConfig,
    _Text2VecOpenAIConfig,
    _Text2VecPalmConfig,
    _Text2VecTransformersConfig,
    AWSModel,
    CohereModel,
    CohereTruncation,
    JinaModels,
    Multi2VecField,
    OpenAIModel,
    OpenAIType,
    Vectorizers,
    _map_multi2vec_fields,
)
from weaviate.collections.classes.config_vector_index import VectorIndexType

from weaviate.collections.classes.config import _VectorIndexConfigCreate


class _NamedVectorizerConfigCreate(_ConfigCreateModel):
    vectorizer: Vectorizers
    properties: Optional[List[str]] = Field(default=None, min_length=1)

    def _to_dict(self) -> Dict[str, Any]:
        return self._to_vectorizer_dict(self.vectorizer, super()._to_dict())

    @staticmethod
    def _to_vectorizer_dict(vectorizer: Vectorizers, values: Dict[str, Any]) -> Dict[str, Any]:
        return {str(vectorizer.value): values}


class _Text2VecOpenAIConfigNamed(_Text2VecOpenAIConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecContextionaryConfigNamed(_Text2VecContextionaryConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecCohereConfigNamed(_Text2VecCohereConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecAWSConfigNamed(_Text2VecAWSConfig, _NamedVectorizerConfigCreate):
    pass


class _Img2VecNeuralConfigNamed(_Img2VecNeuralConfig, _NamedVectorizerConfigCreate):
    pass


class _Multi2VecClipNamed(_Multi2VecClipConfig, _NamedVectorizerConfigCreate):
    pass


class _Multi2VecBindNamed(_Multi2VecBindConfig, _NamedVectorizerConfigCreate):
    pass


class _Ref2VecCentroidConfigNamed(_Ref2VecCentroidConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecAzureOpenAIConfigNamed(_Text2VecAzureOpenAIConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecGPT4AllConfigNamed(_Text2VecGPT4AllConfig, _NamedVectorizerConfigCreate):
    pass


class _NoneConfigNamed(_NamedVectorizerConfigCreate):
    vectorizer: Vectorizers = Field(default=Vectorizers.NONE, frozen=True, exclude=True)


class _Text2VecHuggingFaceConfigNamed(_Text2VecHuggingFaceConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecPalmConfigNamed(_Text2VecPalmConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecTransformersConfigNamed(_Text2VecTransformersConfig, _NamedVectorizerConfigCreate):
    pass


class _Text2VecJinaConfigNamed(_Text2VecJinaConfig, _NamedVectorizerConfigCreate):
    pass


class _NamedVectorConfigCreate(_ConfigCreateModel):
    name: str
    vectorizer: _NamedVectorizerConfigCreate
    vectorIndexType: VectorIndexType = Field(default=VectorIndexType.HNSW, exclude=True)
    vectorIndexConfig: Optional[_VectorIndexConfigCreate] = Field(
        default=None, alias="vector_index_config"
    )

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict: Dict[str, Any] = {"vectorizer": self.vectorizer._to_dict()}

        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if cls_field in ["name", "vectorizer"] or val is None:  # name is key of the dictionary
                continue

            if isinstance(val, Enum):
                ret_dict[cls_field] = str(val.value)
            ret_dict[cls_field] = val

        return ret_dict


class _NamedVectors:
    @staticmethod
    def none(name: str) -> _NamedVectorConfigCreate:
        """Create a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`."""
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_NoneConfigNamed(),
        )

    @staticmethod
    def text2vec_cohere(
        name: str,
        properties: Optional[List[str]] = None,
        model: Optional[Union[CohereModel, str]] = None,
        truncate: Optional[CohereTruncation] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`."""
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecCohereConfigNamed(
                properties=properties,
                baseURL=base_url,
                model=model,
                truncate=truncate,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_contextionary(
        name: str, properties: Optional[List[str]] = None, vectorize_collection_name: bool = True
    ) -> _NamedVectorConfigCreate:
        """Create a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`."""
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecContextionaryConfigNamed(
                properties=properties,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_openai(
        name: str,
        properties: Optional[List[str]] = None,
        model: Optional[Union[OpenAIModel, str]] = None,
        model_version: Optional[str] = None,
        type_: Optional[OpenAIType] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`."""
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecOpenAIConfigNamed(
                properties=properties,
                baseURL=base_url,
                model=model,
                modelVersion=model_version,
                type_=type_,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_aws(
        name: str,
        model: Union[AWSModel, str],
        region: str,
        vectorize_collection_name: bool = True,
        properties: Optional[List[str]] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a `VectorizerConfig` object with the vectorizer set to `Vectorizer.NONE`."""
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecAWSConfigNamed(
                properties=properties,
                model=model,
                region=region,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def img2vec_neural(name: str, image_fields: List[str]) -> _NamedVectorConfigCreate:
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
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Img2VecNeuralConfigNamed(imageFields=image_fields),
        )

    @staticmethod
    def multi2vec_clip(
        name: str,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecClipNamed(
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def multi2vec_bind(
        name: str,
        audio_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        depth_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        imu_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        thermal_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecBindNamed(
                audioFields=_map_multi2vec_fields(audio_fields),
                depthFields=_map_multi2vec_fields(depth_fields),
                imageFields=_map_multi2vec_fields(image_fields),
                IMUFields=_map_multi2vec_fields(imu_fields),
                textFields=_map_multi2vec_fields(text_fields),
                thermalFields=_map_multi2vec_fields(thermal_fields),
                videoFields=_map_multi2vec_fields(video_fields),
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def ref2vec_centroid(
        name: str,
        reference_properties: List[str],
        method: Literal["mean"] = "mean",
    ) -> _NamedVectorConfigCreate:
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Ref2VecCentroidConfigNamed(
                referenceProperties=reference_properties,
                method=method,
            ),
        )

    @staticmethod
    def text2vec_azure_openai(
        name: str,
        resource_name: str,
        deployment_id: str,
        properties: Optional[List[str]] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _NamedVectorConfigCreate:
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecAzureOpenAIConfigNamed(
                properties=properties,
                baseURL=base_url,
                resourceName=resource_name,
                deploymentId=deployment_id,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_gpt4all(
        name: str,
        properties: Optional[List[str]] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_gpt4all` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecGPT4AllConfigNamed(
                properties=properties,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_huggingface(
        name: str,
        properties: Optional[List[str]] = None,
        model: Optional[str] = None,
        passage_model: Optional[str] = None,
        query_model: Optional[str] = None,
        endpoint_url: Optional[AnyHttpUrl] = None,
        wait_for_model: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_huggingface` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `properties`
                Which properties should be included when vectorizing. By default all text properties are included.
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
                    See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface) for more details.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecHuggingFaceConfigNamed(
                properties=properties,
                model=model,
                passageModel=passage_model,
                queryModel=query_model,
                endpointURL=endpoint_url,
                waitForModel=wait_for_model,
                useGPU=use_gpu,
                useCache=use_cache,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_palm(
        name: str,
        project_id: str,
        properties: Optional[List[str]] = None,
        api_endpoint: Optional[AnyHttpUrl] = None,
        model_id: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_palm` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-palm)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `project_id`
                The project ID to use, REQUIRED.
            `api_endpoint`
                The API endpoint to use. Defaults to `None`, which uses the server-defined default.
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecPalmConfigNamed(
                properties=properties,
                projectId=project_id,
                apiEndpoint=api_endpoint,
                modelId=model_id,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_transformers(
        name: str,
        properties: Optional[List[str]] = None,
        pooling_strategy: Literal["masked_mean", "cls"] = "masked_mean",
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_transformers` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-transformers)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `pooling_strategy`
                The pooling strategy to use. Defaults to `masked_mean`.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecTransformersConfigNamed(
                properties=properties,
                poolingStrategy=pooling_strategy,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

    @staticmethod
    def text2vec_jinaai(
        name: str,
        properties: Optional[List[str]] = None,
        model: Optional[Union[JinaModels, str]] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec-jinaai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-jinaai)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-jinaai#available-models) for more details.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Text2VecJinaConfigNamed(
                properties=properties,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
        )

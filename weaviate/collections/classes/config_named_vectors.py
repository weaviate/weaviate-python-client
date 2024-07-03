import warnings
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AnyHttpUrl, Field

from weaviate.collections.classes.config_base import (
    _ConfigCreateModel,
    _ConfigUpdateModel,
    _EnumLikeStr,
)
from weaviate.collections.classes.config_vector_index import (
    _VectorIndexConfigCreate,
    _VectorIndexConfigHNSWUpdate,
    _VectorIndexConfigFlatUpdate,
    _VectorIndexConfigDynamicUpdate,
    _VectorIndexConfigUpdate,
    VectorIndexType,
)
from weaviate.collections.classes.config_vectorizers import (
    _Img2VecNeuralConfigCreate,
    _Multi2VecBindConfigCreate,
    _Multi2VecClipConfigCreate,
    _Multi2VecPalmConfig,
    _Ref2VecCentroidConfigCreate,
    _Text2VecAWSConfigCreate,
    _Text2VecAzureOpenAIConfigCreate,
    _Text2VecCohereConfigCreate,
    _Text2VecContextionaryConfigCreate,
    _Text2VecGPT4AllConfigCreate,
    _Text2VecHuggingFaceConfigCreate,
    _Text2VecJinaConfigCreate,
    _Text2VecOctoConfig,
    _Text2VecOllamaConfig,
    _Text2VecOpenAIConfigCreate,
    _Text2VecPalmConfigCreate,
    _Text2VecTransformersConfigCreate,
    _Text2VecVoyageConfigCreate,
    _VectorizerConfigCreate,
    AWSModel,
    AWSService,
    CohereModel,
    CohereTruncation,
    JinaModel,
    Multi2VecField,
    OpenAIModel,
    OpenAIType,
    Vectorizers,
    VoyageModel,
    _map_multi2vec_fields,
    _VectorizerCustomConfig,
)


class _NamedVectorizerConfigCreate(_ConfigCreateModel):
    vectorizer: Vectorizers
    properties: Optional[List[str]] = Field(default=None, min_length=1, alias="source_properties")

    def _to_dict(self) -> Dict[str, Any]:
        return self._to_vectorizer_dict(self.vectorizer, super()._to_dict())

    @staticmethod
    def _to_vectorizer_dict(vectorizer: Vectorizers, values: Dict[str, Any]) -> Dict[str, Any]:
        return {str(vectorizer.value): values}


class _NamedVectorConfigCreate(_ConfigCreateModel):
    name: str
    properties: Optional[List[str]] = Field(default=None, min_length=1, alias="source_properties")
    vectorizer: _VectorizerConfigCreate
    vectorIndexType: VectorIndexType = Field(default=VectorIndexType.HNSW, exclude=True)
    vectorIndexConfig: Optional[_VectorIndexConfigCreate] = Field(
        default=None, alias="vector_index_config"
    )

    def _to_dict(self) -> Dict[str, Any]:
        ret_dict: Dict[str, Any] = self.__parse_vectorizer()
        if self.vectorIndexConfig is not None:
            ret_dict["vectorIndexType"] = self.vectorIndexConfig.vector_index_type().value
            ret_dict["vectorIndexConfig"] = self.vectorIndexConfig._to_dict()
        else:
            ret_dict["vectorIndexType"] = self.vectorIndexType.value
        return ret_dict

    def __parse_vectorizer(self) -> Dict[str, Any]:
        vectorizer_options = self.vectorizer._to_dict()
        if self.properties is not None:
            vectorizer_options["properties"] = self.properties
        return {"vectorizer": {self.vectorizer.vectorizer.value: vectorizer_options}}


class _NamedVectorConfigUpdate(_ConfigUpdateModel):
    name: str
    vectorIndexConfig: _VectorIndexConfigUpdate = Field(..., alias="vector_index_config")


class _NamedVectors:
    @staticmethod
    def none(
        name: str, *, vector_index_config: Optional[_VectorIndexConfigCreate] = None
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using no vectorizer. You will need to provide the vectors yourself.

        Arguments:
            `name`
                The name of the named vector.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_VectorizerConfigCreate(vectorizer=Vectorizers.NONE),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def custom(
        name: str,
        *,
        module_name: str,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        module_config: Optional[Dict[str, Any]] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using no vectorizer. You will need to provide the vectors yourself.

        Arguments:
            `name`
                The name of the named vector.
            `module_name`
                The name of the custom module to use.
            `module_config`
                The configuration of the custom module to use.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_VectorizerCustomConfig(
                vectorizer=_EnumLikeStr(module_name), module_config=module_config
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_cohere(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
        model: Optional[Union[CohereModel, str]] = None,
        truncate: Optional[CohereTruncation] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_cohere` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-cohere)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `truncate`
                The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        Raises:
            `pydantic.ValidationError` if `truncate` is not a valid value from the `CohereModel` type.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecCohereConfigCreate(
                baseURL=base_url,
                model=model,
                truncate=truncate,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_contextionary(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_contextionary` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-contextionary)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecContextionaryConfigCreate(
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_octoai(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec-octoai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-octoai)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.

        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecOctoConfig(
                baseURL=base_url,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_ollama(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        model: Optional[str] = None,
        api_endpoint: Optional[str] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec-ollama` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-ollama)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `api_endpoint`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
                Docker users may need to specify an alias, such as `http://host.docker.internal:11434` so that the container can access the host machine.

        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecOllamaConfig(
                apiEndpoint=api_endpoint,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_openai(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        model: Optional[Union[OpenAIModel, str]] = None,
        model_version: Optional[str] = None,
        type_: Optional[OpenAIType] = None,
        base_url: Optional[AnyHttpUrl] = None,
        dimensions: Optional[int] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_openai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-openai)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
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
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecOpenAIConfigCreate(
                baseURL=base_url,
                model=model,
                modelVersion=model_version,
                type_=type_,
                vectorizeClassName=vectorize_collection_name,
                dimensions=dimensions,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_aws(
        name: str,
        region: str,
        *,
        model: Optional[Union[AWSModel, str]] = None,
        endpoint: Optional[str] = None,
        service: Union[AWSService, str] = "bedrock",
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_aws` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-aws)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `region`
                The AWS region to run the model from, REQUIRED.
            `model`
                The model to use.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecAWSConfigCreate(
                model=model,
                endpoint=endpoint,
                region=region,
                service=service,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def img2vec_neural(
        name: str,
        image_fields: List[str],
        *,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a `Img2VecNeuralConfig` object for use when vectorizing using the `img2vec-neural` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/img2vec-neural)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `image_fields`
                The image fields to use. This is a required field and must match the property fields
                of the collection that are defined as `DataType.BLOB`.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default

        Raises:
            `pydantic.ValidationError` if `image_fields` is not a `list`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Img2VecNeuralConfigCreate(imageFields=image_fields),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def multi2vec_clip(
        name: str,
        *,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        interference_url: Optional[str] = None,
        inference_url: Optional[str] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `multi2vec_clip` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `image_fields`
                The image fields to use in vectorization.
            `text_fields`
                The text fields to use in vectorization.
            `inference_url`
                The inference url to use where API requests should go. Defaults to `None`, which uses the server-defined default.
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

        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecClipConfigCreate(
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
                vectorizeClassName=vectorize_collection_name,
                inferenceUrl=inference_url,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def multi2vec_palm(
        name: str,
        *,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        location: str,
        project_id: str,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        dimensions: Optional[int] = None,
        video_interval_seconds: Optional[int] = None,
        model_id: Optional[str] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `multi2vec_clip` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
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
            `video_interval_seconds`
                Length of a video interval. Defaults to `None`, which uses the server-defined default.
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecPalmConfig(
                projectId=project_id,
                location=location,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
                videoFields=_map_multi2vec_fields(video_fields),
                dimensions=dimensions,
                modelId=model_id,
                videoIntervalSeconds=video_interval_seconds,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def multi2vec_bind(
        name: str,
        *,
        audio_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        depth_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        imu_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        thermal_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `multi2vec_bind` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecBindConfigCreate(
                audioFields=_map_multi2vec_fields(audio_fields),
                depthFields=_map_multi2vec_fields(depth_fields),
                imageFields=_map_multi2vec_fields(image_fields),
                IMUFields=_map_multi2vec_fields(imu_fields),
                textFields=_map_multi2vec_fields(text_fields),
                thermalFields=_map_multi2vec_fields(thermal_fields),
                videoFields=_map_multi2vec_fields(video_fields),
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def ref2vec_centroid(
        name: str,
        reference_properties: List[str],
        *,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        method: Literal["mean"] = "mean",
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `ref2vec_centroid` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `reference_properties`
                The reference properties to use in vectorization, REQUIRED.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            vectorizer=_Ref2VecCentroidConfigCreate(
                referenceProperties=reference_properties,
                method=method,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_azure_openai(
        name: str,
        resource_name: str,
        deployment_id: str,
        *,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        source_properties: Optional[List[str]] = None,
        vectorize_collection_name: bool = True,
        base_url: Optional[AnyHttpUrl] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_azure_openai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecAzureOpenAIConfigCreate(
                baseURL=base_url,
                resourceName=resource_name,
                deploymentId=deployment_id,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_gpt4all(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_gpt4all` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecGPT4AllConfigCreate(
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_huggingface(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        model: Optional[str] = None,
        passage_model: Optional[str] = None,
        query_model: Optional[str] = None,
        endpoint_url: Optional[AnyHttpUrl] = None,
        wait_for_model: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        use_cache: Optional[bool] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_huggingface` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
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

        Raises:
            `pydantic.ValidationError` if the arguments passed to the function are invalid.
                It is important to note that some of these variables are mutually exclusive.
                    See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-huggingface) for more details.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecHuggingFaceConfigCreate(
                model=model,
                passageModel=passage_model,
                queryModel=query_model,
                endpointURL=endpoint_url,
                waitForModel=wait_for_model,
                useGPU=use_gpu,
                useCache=use_cache,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_palm(
        name: str,
        project_id: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        api_endpoint: Optional[str] = None,
        model_id: Optional[str] = None,
        title_property: Optional[str] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_palm` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-palm)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `project_id`
                The project ID to use, REQUIRED.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `api_endpoint`
                The API endpoint to use without a leading scheme such as `http://`. Defaults to `None`, which uses the server-defined default
            `model_id`
                The model ID to use. Defaults to `None`, which uses the server-defined default.
            `title_property`
                The Weaviate property name for the `gecko-002` or `gecko-003` model to use as the title.

        Raises:
            `pydantic.ValidationError` if `api_endpoint` is not a valid URL.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecPalmConfigCreate(
                projectId=project_id,
                apiEndpoint=api_endpoint,
                modelId=model_id,
                vectorizeClassName=vectorize_collection_name,
                titleProperty=title_property,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_transformers(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        pooling_strategy: Literal["masked_mean", "cls"] = "masked_mean",
        inference_url: Optional[str] = None,
        passage_inference_url: Optional[str] = None,
        query_inference_url: Optional[str] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec_transformers` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-transformers)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `pooling_strategy`
                The pooling strategy to use. Defaults to `masked_mean`.
            `inference_url`
                The inferenceUrl to use where API requests should go. You can use either this OR passage/query_inference_url. Defaults to `None`, which uses the server-defined default.
            `passage_inference_url`
                The inferenceUrl to use where passage API requests should go. You can use either this and query_inference_url OR inference_url. Defaults to `None`, which uses the server-defined default.
            `query_inference_url`
                The inferenceUrl to use where query API requests should go. You can use either this and passage_inference_url OR inference_url. Defaults to `None`, which uses the server-defined default.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecTransformersConfigCreate(
                poolingStrategy=pooling_strategy,
                vectorizeClassName=vectorize_collection_name,
                inferenceUrl=inference_url,
                passageInferenceUrl=passage_inference_url,
                queryInferenceUrl=query_inference_url,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_jinaai(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        model: Optional[Union[JinaModel, str]] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec-jinaai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-jinaai)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-jinaai#available-models) for more details.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecJinaConfigCreate(
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=vector_index_config,
        )

    @staticmethod
    def text2vec_voyageai(
        name: str,
        *,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
        model: Optional[Union[VoyageModel, str]] = None,
        base_url: Optional[str] = None,
        truncate: Optional[bool] = None,
    ) -> _NamedVectorConfigCreate:
        """Create a named vector using the `text2vec-jinaai` model.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-jinaai)
        for detailed usage.

        Arguments:
            `name`
                The name of the named vector.
            `source_properties`
                Which properties should be included when vectorizing. By default all text properties are included.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use wvc.config.Configure.VectorIndex to create a vector index configuration. None by default
            `vectorize_collection_name`
                Whether to vectorize the collection name. Defaults to `True`.
            `model`
                The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-voyageai#available-models) for more details.
            `base_url`
                The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            `truncate`
                Whether to truncate the input texts to fit within the context length. Defaults to `None`, which uses the server-defined default.
        """
        return _NamedVectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecVoyageConfigCreate(
                model=model,
                vectorizeClassName=vectorize_collection_name,
                baseURL=base_url,
                truncate=truncate,
            ),
            vector_index_config=vector_index_config,
        )


class _NamedVectorsUpdate:
    @staticmethod
    def update(
        name: str,
        *,
        vector_index_config: Union[
            _VectorIndexConfigHNSWUpdate,
            _VectorIndexConfigFlatUpdate,
            _VectorIndexConfigDynamicUpdate,
        ],
    ) -> _NamedVectorConfigUpdate:
        """Update the vector index configuration of a named vector.

        This is the only update operation allowed currently. If you wish to change the vectorization configuration itself, you will have to
        recreate the collection with the new configuration.

        Arguments:
            `name`
                The name of the named vector.
            `vector_index_config`
                The configuration for Weaviate's vector index. Use `wvc.config.Reconfigure.VectorIndex` to create a vector index configuration. `None` by default
        """
        return _NamedVectorConfigUpdate(
            name=name,
            vector_index_config=vector_index_config,
        )

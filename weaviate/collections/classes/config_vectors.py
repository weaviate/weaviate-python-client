from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import AnyHttpUrl, Field
from typing_extensions import deprecated as typing_deprecated

from weaviate.collections.classes.config_base import (
    _ConfigCreateModel,
    _ConfigUpdateModel,
    _EnumLikeStr,
)
from weaviate.collections.classes.config_vector_index import (
    VectorIndexType,
    _MultiVectorConfigCreate,
    _MultiVectorEncodingConfigCreate,
    _QuantizerConfigCreate,
    _VectorIndexConfigCreate,
    _VectorIndexConfigDynamicCreate,
    _VectorIndexConfigDynamicUpdate,
    _VectorIndexConfigFlatCreate,
    _VectorIndexConfigFlatUpdate,
    _VectorIndexConfigHNSWCreate,
    _VectorIndexConfigHNSWUpdate,
    _VectorIndexConfigUpdate,
)
from weaviate.collections.classes.config_vectorizers import (
    AWSModel,
    AWSService,
    CohereModel,
    CohereMultimodalModel,
    CohereTruncation,
    JinaModel,
    JinaMultimodalModel,
    Multi2VecField,
    OpenAIModel,
    OpenAIType,
    Vectorizers,
    VoyageModel,
    VoyageMultimodalModel,
    WeaviateModel,
    _Img2VecNeuralConfig,
    _map_multi2vec_fields,
    _Multi2MultiVecJinaConfig,
    _Multi2VecAWSConfig,
    _Multi2VecBindConfig,
    _Multi2VecClipConfig,
    _Multi2VecCohereConfig,
    _Multi2VecGoogleConfig,
    _Multi2VecJinaConfig,
    _Multi2VecNvidiaConfig,
    _Multi2VecVoyageaiConfig,
    _Ref2VecCentroidConfig,
    _Text2ColbertJinaAIConfig,
    _Text2VecAWSConfig,
    _Text2VecAzureOpenAIConfig,
    _Text2VecCohereConfig,
    _Text2VecContextionaryConfig,
    _Text2VecDatabricksConfig,
    _Text2VecGoogleConfig,
    _Text2VecGPT4AllConfig,
    _Text2VecHuggingFaceConfig,
    _Text2VecJinaConfig,
    _Text2VecMistralConfig,
    _Text2VecModel2VecConfig,
    _Text2VecMorphConfig,
    _Text2VecNvidiaConfig,
    _Text2VecOllamaConfig,
    _Text2VecOpenAIConfig,
    _Text2VecTransformersConfig,
    _Text2VecVoyageConfig,
    _Text2VecWeaviateConfig,
    _VectorizerConfigCreate,
    _VectorizerCustomConfig,
)


class _VectorConfigCreate(_ConfigCreateModel):
    name: Optional[str]
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


class _VectorConfigUpdate(_ConfigUpdateModel):
    name: str
    vectorIndexConfig: _VectorIndexConfigUpdate = Field(..., alias="vector_index_config")


class _IndexWrappers:
    @staticmethod
    def __hnsw(
        *,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        multivector: Optional[_MultiVectorConfigCreate] = None,
    ) -> _VectorIndexConfigHNSWCreate:
        return _VectorIndexConfigHNSWCreate(
            cleanupIntervalSeconds=None,
            distance=None,
            dynamicEfMin=None,
            dynamicEfMax=None,
            dynamicEfFactor=None,
            efConstruction=None,
            ef=None,
            filterStrategy=None,
            flatSearchCutoff=None,
            maxConnections=None,
            vectorCacheMaxObjects=None,
            quantizer=quantizer,
            multivector=multivector,
        )

    @staticmethod
    def __flat(*, quantizer: Optional[_QuantizerConfigCreate]) -> _VectorIndexConfigFlatCreate:
        return _VectorIndexConfigFlatCreate(
            distance=None,
            vectorCacheMaxObjects=None,
            quantizer=quantizer,
            multivector=None,
        )

    @staticmethod
    def single(
        vector_index_config: Optional[_VectorIndexConfigCreate],
        quantizer: Optional[_QuantizerConfigCreate],
    ) -> Optional[_VectorIndexConfigCreate]:
        if quantizer is not None:
            if vector_index_config is None:
                vector_index_config = _IndexWrappers.__hnsw(quantizer=quantizer)
            else:
                if isinstance(vector_index_config, _VectorIndexConfigDynamicCreate):
                    if vector_index_config.hnsw is None:
                        vector_index_config.hnsw = _IndexWrappers.__hnsw(quantizer=quantizer)
                    else:
                        vector_index_config.hnsw.quantizer = quantizer
                    if vector_index_config.flat is None:
                        vector_index_config.flat = _IndexWrappers.__flat(quantizer=quantizer)
                    else:
                        vector_index_config.flat.quantizer = quantizer
                else:
                    vector_index_config.quantizer = quantizer
        return vector_index_config

    @staticmethod
    def multi(
        vector_index_config: Optional[_VectorIndexConfigCreate],
        quantizer: Optional[_QuantizerConfigCreate],
        multi_vector_config: Optional[_MultiVectorConfigCreate],
        encoding: Optional[_MultiVectorEncodingConfigCreate],
    ) -> Optional[_VectorIndexConfigCreate]:
        if multi_vector_config is None:
            multi_vector_config = _MultiVectorConfigCreate(aggregation=None, encoding=None)
        if encoding is not None:
            multi_vector_config.encoding = encoding
        if vector_index_config is None:
            vector_index_config = _IndexWrappers.__hnsw(multivector=multi_vector_config)
        else:
            vector_index_config.multivector = multi_vector_config
        return _IndexWrappers.single(vector_index_config, quantizer)


class _MultiVectors:
    @staticmethod
    def self_provided(
        *,
        name: Optional[str] = None,
        encoding: Optional[_MultiVectorEncodingConfigCreate] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        multi_vector_config: Optional[_MultiVectorConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ):
        """Create a multi-vector using no vectorizer. You will need to provide the vectors yourself.

        Args:
            name: The name of the vector.
            encoding: The type of multi-vector encoding to use in the vector index. Defaults to `None`, which uses the server-defined default.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            multi_vector_config: The configuration for the multi-vector index. Use `wvc.config.Configure.VectorIndex.MultiVector` to create a multi-vector configuration. None by default
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_VectorizerConfigCreate(vectorizer=Vectorizers.NONE),
            vector_index_config=_IndexWrappers.multi(
                vector_index_config, quantizer, multi_vector_config, encoding
            ),
        )

    @staticmethod
    def text2vec_jinaai(
        *,
        name: Optional[str] = None,
        encoding: Optional[_MultiVectorEncodingConfigCreate] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        dimensions: Optional[int] = None,
        model: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        multi_vector_config: Optional[_MultiVectorConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a multi-vector using the `text2colbert-jinaai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/colbert) for detailed usage.

        Args:
            name: The name of the vector.
            encoding: The type of multi-vector encoding to use in the vector index. Defaults to `None`, which uses the server-defined default.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            dimensions: Number of dimensions. Applicable to v3 OpenAI models only. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            encoding: The type of multi-vector encoding to use in the vector index. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            multi_vector_config: The configuration for the multi-vector index. Use `wvc.config.Configure.VectorIndex.MultiVector` to create a multi-vector configuration. None by default
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vector_index_config=_IndexWrappers.multi(
                vector_index_config, quantizer, multi_vector_config, encoding
            ),
            vectorizer=_Text2ColbertJinaAIConfig(
                model=model, dimensions=dimensions, vectorizeClassName=vectorize_collection_name
            ),
        )

    @staticmethod
    def multi2vec_jinaai(
        *,
        name: Optional[str] = None,
        encoding: Optional[_MultiVectorEncodingConfigCreate] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        model: Optional[Union[JinaMultimodalModel, str]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        multi_vector_config: Optional[_MultiVectorConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2multivec-jinaai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            encoding: The type of multi-vector encoding to use in the vector index. Defaults to `None`, which uses the server-defined default.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            text_fields: The text fields to use in vectorization.
            multi_vector_config: The configuration for the multi-vector index. Use `wvc.config.Configure.VectorIndex.MultiVector` to create a multi-vector configuration. None by default
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `JinaMultimodalModel` type.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2MultiVecJinaConfig(
                baseURL=base_url,
                model=model,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
            ),
            vector_index_config=_IndexWrappers.multi(
                vector_index_config, quantizer, multi_vector_config, encoding
            ),
        )


class _Vectors:
    @staticmethod
    def self_provided(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ):
        """Create a vector using no vectorizer. You will need to provide the vectors yourself.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_VectorizerConfigCreate(vectorizer=Vectorizers.NONE),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def custom(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        module_name: str,
        module_config: Optional[Dict[str, Any]] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using a custom module that is not currently supported by the SDK.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            module_name: The name of the custom module to use.
            module_config: The configuration of the custom module to use.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_VectorizerCustomConfig(
                vectorizer=_EnumLikeStr(module_name), module_config=module_config
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_cohere(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        model: Optional[Union[CohereModel, str]] = None,
        truncate: Optional[CohereTruncation] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-cohere` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/cohere/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            truncate: The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `CohereModel` type or if `truncate` is not a valid value from the `CohereTruncation` type.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecCohereConfig(
                baseURL=base_url,
                model=model,
                truncate=truncate,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_cohere(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        model: Optional[Union[CohereMultimodalModel, str]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        truncate: Optional[CohereTruncation] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec_cohere` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/cohere/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            text_fields: The text fields to use in vectorization.
            truncate: The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `CohereMultimodalModel` type or if `truncate` is not a valid value from the `CohereTruncation` type.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecCohereConfig(
                baseURL=base_url,
                model=model,
                truncate=truncate,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    @typing_deprecated(
        "The contextionary model is old and not recommended for use. If you are looking for a local, lightweight model try the new text2vec-model2vec module instead."
    )
    def text2vec_contextionary(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec_contextionary` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-contextionary)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecContextionaryConfig(
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_model2vec(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        inference_url: Optional[str] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec_model2vec` module.

        See the [documentation](https://docs.weaviate.io/weaviate/model-providers/model2vec)
        for detailed usage.

        Args:
            name: The name of the vector.
            inference_url: The inferenceUrl to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecModel2VecConfig(
                vectorizeClassName=vectorize_collection_name,
                inferenceUrl=inference_url,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_databricks(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        endpoint: str,
        instruction: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-databricks` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/databricks/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            endpoint: The endpoint to use.
            instruction: The instruction strategy to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecDatabricksConfig(
                endpoint=endpoint,
                instruction=instruction,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_mistral(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        model: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-mistral` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/mistral/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecMistralConfig(
                baseURL=base_url,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_morph(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        model: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-morph` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/morph/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecMorphConfig(
                baseURL=base_url,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_ollama(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        api_endpoint: Optional[str] = None,
        model: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-ollama` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/ollama/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            api_endpoint: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
                Docker users may need to specify an alias, such as `http://host.docker.internal:11434` so that the container can access the host machine.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.


        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecOllamaConfig(
                apiEndpoint=api_endpoint,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_openai(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        dimensions: Optional[int] = None,
        model: Optional[Union[OpenAIModel, str]] = None,
        model_version: Optional[str] = None,
        type_: Optional[OpenAIType] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-openai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/openai/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            dimensions: Number of dimensions. Applicable to v3 OpenAI models only. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            model_version: The model version to use. Defaults to `None`, which uses the server-defined default.
            type_: The type of model to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            pydantic.ValidationError: If `type_` is not a valid value from the `OpenAIType` type.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecOpenAIConfig(
                baseURL=base_url,
                model=model,
                modelVersion=model_version,
                type_=type_,
                vectorizeClassName=vectorize_collection_name,
                dimensions=dimensions,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_aws(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        endpoint: Optional[str] = None,
        model: Optional[Union[AWSModel, str]] = None,
        region: str,
        service: Union[AWSService, str] = "bedrock",
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/aws/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            endpoint: The endpoint to use. Defaults to `None`, which uses the server-defined default.
            model: The model to use.
            region: The AWS region to run the model from, REQUIRED.
            service: The AWS service to use. Defaults to `bedrock`.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecAWSConfig(
                model=model,
                endpoint=endpoint,
                region=region,
                service=service,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_aws(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        dimensions: Optional[int] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        model: Optional[str] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        region: Optional[str] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-aws` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/aws/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            dimensions: The number of dimensions to use. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            text_fields: The text fields to use in vectorization.
            region: The AWS region to run the model from. Defaults to `None`, which uses the server-defined defau
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `JinaMultimodalModel` type.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecAWSConfig(
                region=region,
                model=model,
                dimensions=dimensions,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def img2vec_neural(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        image_fields: List[str],
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `img2vec-neural` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/img2vec-neural)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            image_fields: The image fields to use. This is a required field and must match the property fields of the collection that are defined as `DataType.BLOB`.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `image_fields` is not a `list`.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Img2VecNeuralConfig(imageFields=image_fields),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_clip(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        inference_url: Optional[str] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-clip` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/transformers/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            inference_url: The inference url to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            text_fields: The text fields to use in vectorization.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecClipConfig(
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
                inferenceUrl=inference_url,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_google(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        dimensions: Optional[int] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        location: str,
        model: Optional[str] = None,
        project_id: str,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_interval_seconds: Optional[int] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-google` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/google/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            dimensions: The number of dimensions to use. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            location: Where the model runs. REQUIRED.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            project_id: The project ID to use, REQUIRED.
            text_fields: The text fields to use in vectorization.
            video_fields: The video fields to use in vectorization.
            video_interval_seconds: Length of a video interval. Defaults to `None`, which uses the server-defined default.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecGoogleConfig(
                projectId=project_id,
                location=location,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
                videoFields=_map_multi2vec_fields(video_fields),
                dimensions=dimensions,
                modelId=model,
                videoIntervalSeconds=video_interval_seconds,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_bind(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        audio_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        depth_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        imu_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        thermal_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        video_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-bind` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/imagebind/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            audio_fields: The audio fields to use in vectorization.
            depth_fields: The depth fields to use in vectorization.
            image_fields: The image fields to use in vectorization.
            imu_fields: The IMU fields to use in vectorization.
            text_fields: The text fields to use in vectorization.
            thermal_fields: The thermal fields to use in vectorization.
            video_fields: The video fields to use in vectorization.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecBindConfig(
                audioFields=_map_multi2vec_fields(audio_fields),
                depthFields=_map_multi2vec_fields(depth_fields),
                imageFields=_map_multi2vec_fields(image_fields),
                IMUFields=_map_multi2vec_fields(imu_fields),
                textFields=_map_multi2vec_fields(text_fields),
                thermalFields=_map_multi2vec_fields(thermal_fields),
                videoFields=_map_multi2vec_fields(video_fields),
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_voyageai(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        model: Optional[Union[VoyageMultimodalModel, str]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        truncation: Optional[bool] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-voyageai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/voyageai/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            output_encoding: The output encoding to use. Defaults to `None`, which uses the server-defined default.
            text_fields: The text fields to use in vectorization.
            truncation: The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `VoyageaiMultimodalModel` type.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecVoyageaiConfig(
                baseURL=base_url,
                model=model,
                truncation=truncation,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_nvidia(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        model: Optional[str] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        truncation: Optional[bool] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-nvidia` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/nvidia/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            text_fields: The text fields to use in vectorization.
            truncation: The truncation strategy to use. Defaults to `None`, which uses the server-defined default.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `NvidiaMultimodalModel` type.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecNvidiaConfig(
                baseURL=base_url,
                model=model,
                truncation=truncation,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def ref2vec_centroid(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        method: Literal["mean"] = "mean",
        reference_properties: List[str],
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `ref2vec-centroid` module.

        See the [documentation](https://weaviate.io/developers/weaviate/modules/retriever-vectorizer-modules/text2vec-gpt4all)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            method: The method to use. Defaults to `mean`.
            reference_properties: The reference properties to use in vectorization, REQUIRED.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Ref2VecCentroidConfig(
                referenceProperties=reference_properties,
                method=method,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_azure_openai(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        deployment_id: str,
        dimensions: Optional[int] = None,
        model: Optional[str] = None,
        resource_name: str,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-openai` module running with Azure.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/openai-azure/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            deployment_id: The deployment ID to use, REQUIRED.
            dimensions: The dimensionality of the vectors. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            resource_name: The resource name to use, REQUIRED.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecAzureOpenAIConfig(
                baseURL=base_url,
                dimensions=dimensions,
                model=model,
                resourceName=resource_name,
                deploymentId=deployment_id,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    @typing_deprecated(
        "The `text2vec-gpt4all` vectorizer is deprecated and will be removed in a future release. See the docs (https://docs.weaviate.io/weaviate/model-providers) for alternatives."
    )
    def text2vec_gpt4all(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-gpt4all` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/gpt4all/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecGPT4AllConfig(
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_huggingface(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        endpoint_url: Optional[AnyHttpUrl] = None,
        model: Optional[str] = None,
        passage_model: Optional[str] = None,
        query_model: Optional[str] = None,
        wait_for_model: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-huggingface` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/huggingface/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            endpoint_url: The endpoint URL to use. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            passage_model: The passage model to use. Defaults to `None`, which uses the server-defined default.
            query_model: The query model to use. Defaults to `None`, which uses the server-defined default.
            wait_for_model: Whether to wait for the model to be loaded. Defaults to `None`, which uses the server-defined default.
            use_gpu: Whether to use the GPU. Defaults to `None`, which uses the server-defined default.
            use_cache: Whether to use the cache. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            pydantic.ValidationError: If the arguments passed to the function are invalid.
                It is important to note that some of these variables are mutually exclusive.
                See the [documentation](https://weaviate.io/developers/weaviate/model-providers/huggingface/embeddings#vectorizer-parameters) for more details.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecHuggingFaceConfig(
                model=model,
                passageModel=passage_model,
                queryModel=query_model,
                endpointURL=endpoint_url,
                waitForModel=wait_for_model,
                useGPU=use_gpu,
                useCache=use_cache,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_google(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        api_endpoint: Optional[str] = None,
        dimensions: Optional[int] = None,
        model: Optional[str] = None,
        project_id: str,
        title_property: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-google` model.

        See the [documentation]https://weaviate.io/developers/weaviate/model-providers/google/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            api_endpoint: The API endpoint to use without a leading scheme such as `http://`. Defaults to `None`, which uses the server-defined default.
            dimensions: The dimensionality of the vectors. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            project_id: The project ID to use, REQUIRED.
            title_property: The Weaviate property name for the `gecko-002` or `gecko-003` model to use as the title.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default.
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            pydantic.ValidationError: If `api_endpoint` is not a valid URL.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecGoogleConfig(
                projectId=project_id,
                apiEndpoint=api_endpoint,
                dimensions=dimensions,
                modelId=model,
                vectorizeClassName=vectorize_collection_name,
                titleProperty=title_property,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_google_aistudio(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        dimensions: Optional[int] = None,
        model: Optional[str] = None,
        title_property: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-google` model.

        See the [documentation]https://weaviate.io/developers/weaviate/model-providers/google/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            dimenions: The dimensionality of the vectors. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            title_property: The Weaviate property name for the `gecko-002` or `gecko-003` model to use as the title.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.

        Raises:
            pydantic.ValidationError: If `api_endpoint` is not a valid URL.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecGoogleConfig(
                projectId=None,
                apiEndpoint="generativelanguage.googleapis.com",
                dimensions=dimensions,
                modelId=model,
                vectorizeClassName=vectorize_collection_name,
                titleProperty=title_property,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_transformers(
        *,
        name: Optional[str] = None,
        dimensions: Optional[int] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        inference_url: Optional[str] = None,
        passage_inference_url: Optional[str] = None,
        pooling_strategy: Literal["masked_mean", "cls"] = "masked_mean",
        query_inference_url: Optional[str] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-transformers` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/transformers/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            dimensions: The number of dimensions for the generated embeddings. Defaults to `None`, which uses the server-defined default.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            inference_url: The inferenceUrl to use where API requests should go. You can use either this OR passage/query_inference_url. Defaults to `None`, which uses the server-defined default.
            passage_inference_url: The inferenceUrl to use where passage API requests should go. You can use either this and query_inference_url OR inference_url. Defaults to `None`, which uses the server-defined default.
            pooling_strategy: The pooling strategy to use. Defaults to `masked_mean`.
            query_inference_url: The inferenceUrl to use where query API requests should go. You can use either this and passage_inference_url OR inference_url. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecTransformersConfig(
                poolingStrategy=pooling_strategy,
                dimensions=dimensions,
                vectorizeClassName=vectorize_collection_name,
                inferenceUrl=inference_url,
                passageInferenceUrl=passage_inference_url,
                queryInferenceUrl=query_inference_url,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_jinaai(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[str] = None,
        dimensions: Optional[int] = None,
        model: Optional[Union[JinaModel, str]] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-jinaai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/embeddings) for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to send the vectorization requests to. Defaults to `None`, which uses the server-defined default.
            dimensions: The number of dimensions for the generated embeddings. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecJinaConfig(
                baseURL=base_url,
                dimensions=dimensions,
                model=model,
                vectorizeClassName=vectorize_collection_name,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def multi2vec_jinaai(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[AnyHttpUrl] = None,
        dimensions: Optional[int] = None,
        image_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        model: Optional[Union[JinaMultimodalModel, str]] = None,
        text_fields: Optional[Union[List[str], List[Multi2VecField]]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
    ) -> _VectorConfigCreate:
        """Create a vector using the `multi2vec-jinaai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/jinaai/embeddings-multimodal)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            dimensions: The number of dimensions for the generated embeddings (only available for some models). Defaults to `None`, which uses the server-defined default.
            image_fields: The image fields to use in vectorization.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
            text_fields: The text fields to use in vectorization.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default

        Raises:
            pydantic.ValidationError: If `model` is not a valid value from the `JinaMultimodalModel` type.
        """
        return _VectorConfigCreate(
            name=name,
            vectorizer=_Multi2VecJinaConfig(
                baseURL=base_url,
                model=model,
                dimensions=dimensions,
                imageFields=_map_multi2vec_fields(image_fields),
                textFields=_map_multi2vec_fields(text_fields),
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_voyageai(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[str] = None,
        model: Optional[Union[VoyageModel, str]] = None,
        truncate: Optional[bool] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-voyageai` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/voyageai/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/model-providers/voyageai/embeddings#available-models) for more details.
            truncate: Whether to truncate the input texts to fit within the context length. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecVoyageConfig(
                model=model,
                vectorizeClassName=vectorize_collection_name,
                baseURL=base_url,
                truncate=truncate,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_weaviate(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[str] = None,
        dimensions: Optional[int] = None,
        model: Optional[Union[WeaviateModel, str]] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecWeaviateConfig(
                model=model,
                vectorizeClassName=vectorize_collection_name,
                baseURL=base_url,
                dimensions=dimensions,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )

    @staticmethod
    def text2vec_nvidia(
        *,
        name: Optional[str] = None,
        quantizer: Optional[_QuantizerConfigCreate] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        truncate: Optional[bool] = None,
        source_properties: Optional[List[str]] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vectorize_collection_name: bool = True,
    ) -> _VectorConfigCreate:
        """Create a vector using the `text2vec-nvidia` module.

        See the [documentation](https://weaviate.io/developers/weaviate/model-providers/nvidia/embeddings)
        for detailed usage.

        Args:
            name: The name of the vector.
            quantizer: The quantizer to use for the vector index. If not provided, no quantization will be applied.
            base_url: The base URL to use where API requests should go. Defaults to `None`, which uses the server-defined default.
            source_properties: Which properties should be included when vectorizing. By default all text properties are included.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Configure.VectorIndex` to create a vector index configuration. None by default
            vectorize_collection_name: Whether to vectorize the collection name. Defaults to `True`.
            model: The model to use. Defaults to `None`, which uses the server-defined default.
                See the
                [documentation](https://weaviate.io/developers/weaviate/model-providers/nvidia/embeddings#available-models) for more details.

            truncate: Whether to truncate the input texts to fit within the context length. Defaults to `None`, which uses the server-defined default.
        """
        return _VectorConfigCreate(
            name=name,
            source_properties=source_properties,
            vectorizer=_Text2VecNvidiaConfig(
                model=model,
                vectorizeClassName=vectorize_collection_name,
                baseURL=base_url,
                truncate=truncate,
            ),
            vector_index_config=_IndexWrappers.single(vector_index_config, quantizer),
        )


class _VectorsUpdate:
    @staticmethod
    def update(
        *,
        name: Optional[str] = None,
        vector_index_config: Union[
            _VectorIndexConfigHNSWUpdate,
            _VectorIndexConfigFlatUpdate,
            _VectorIndexConfigDynamicUpdate,
        ],
    ) -> _VectorConfigUpdate:
        """Update the vector index configuration of a vector.

        This is the only update operation allowed currently. If you wish to change the vectorization configuration itself, you will have to
        recreate the collection with the new configuration.

        Args:
            name: The name of the vector.
            vector_index_config: The configuration for Weaviate's vector index. Use `wvc.config.Reconfigure.VectorIndex` to create a vector index configuration. `None` by default
        """
        return _VectorConfigUpdate(
            name=name or "default",
            vector_index_config=vector_index_config,
        )

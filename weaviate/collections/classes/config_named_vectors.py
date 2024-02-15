from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import AnyHttpUrl, Field
from weaviate.collections.classes.config_vectorizers import (
    _ConfigCreateModel,
    _Text2VecCohereConfig,
    _Text2VecContextionaryConfig,
    _Text2VecOpenAIConfig,
    CohereModel,
    CohereTruncation,
    OpenAIModel,
    OpenAIType,
    Vectorizers,
)
from weaviate.collections.classes.config_vector_index import VectorIndexType


class _NamedVectorizerConfigCreate(_ConfigCreateModel):
    @staticmethod
    def _to_vectorizer_dict(vectorizer: Vectorizers, values: Dict[str, Any]) -> Dict[str, Any]:
        return {str(vectorizer.value): values}


class _Text2VecOpenAIConfigNamed(_Text2VecOpenAIConfig, _NamedVectorizerConfigCreate):
    properties: Optional[List[str]] = Field(default=None, min_length=1)

    def _to_dict(self) -> Dict[str, Any]:
        return _NamedVectorizerConfigCreate._to_vectorizer_dict(self.vectorizer, super()._to_dict())


class _Text2VecContextionaryConfigNamed(_Text2VecContextionaryConfig, _NamedVectorizerConfigCreate):
    properties: Optional[List[str]] = Field(default=None, min_length=1)

    def _to_dict(self) -> Dict[str, Any]:
        return _NamedVectorizerConfigCreate._to_vectorizer_dict(self.vectorizer, super()._to_dict())


class _Text2VecCohereConfigNamed(_Text2VecCohereConfig, _NamedVectorizerConfigCreate):
    properties: Optional[List[str]] = Field(default=None, min_length=1)

    def _to_dict(self) -> Dict[str, Any]:
        return _NamedVectorizerConfigCreate._to_vectorizer_dict(self.vectorizer, super()._to_dict())


class _NoneConfigNamed(_NamedVectorizerConfigCreate):
    vectorizer: Vectorizers = Field(default=Vectorizers.NONE, frozen=True, exclude=True)

    def _to_dict(self) -> Dict[str, Any]:
        return _NamedVectorizerConfigCreate._to_vectorizer_dict(self.vectorizer, {})


class _NamedVectorConfigCreate(_ConfigCreateModel):
    name: str
    vectorizer: _NamedVectorizerConfigCreate
    vectorIndexType: VectorIndexType = Field(
        default=VectorIndexType.HNSW, alias="vector_index_type"
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
    def text2vec_contectionary(
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

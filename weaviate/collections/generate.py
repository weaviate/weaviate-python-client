from typing import Generic

from weaviate.collections.classes.types import TProperties, References

from weaviate.collections.queries.bm25 import _BM25GenerateAsync, _BM25Generate
from weaviate.collections.queries.fetch_objects import (
    _FetchObjectsGenerateAsync,
    _FetchObjectsGenerate,
)
from weaviate.collections.queries.fetch_objects_by_ids import (
    _FetchObjectsByIDsGenerateAsync,
    _FetchObjectsByIDsGenerate,
)
from weaviate.collections.queries.hybrid import _HybridGenerateAsync, _HybridGenerate
from weaviate.collections.queries.near_image import _NearImageGenerateAsync, _NearImageGenerate
from weaviate.collections.queries.near_media import _NearMediaGenerateAsync, _NearMediaGenerate
from weaviate.collections.queries.near_object import _NearObjectGenerateAsync, _NearObjectGenerate
from weaviate.collections.queries.near_text import _NearTextGenerateAsync, _NearTextGenerate
from weaviate.collections.queries.near_vector import _NearVectorGenerateAsync, _NearVectorGenerate


class _GenerateCollectionAsync(
    Generic[TProperties, References],
    _BM25GenerateAsync[TProperties, References],
    _FetchObjectsGenerateAsync[TProperties, References],
    _FetchObjectsByIDsGenerateAsync[TProperties, References],
    _HybridGenerateAsync[TProperties, References],
    _NearImageGenerateAsync[TProperties, References],
    _NearMediaGenerateAsync[TProperties, References],
    _NearObjectGenerateAsync[TProperties, References],
    _NearTextGenerateAsync[TProperties, References],
    _NearVectorGenerateAsync[TProperties, References],
):
    pass


class _GenerateCollection(
    Generic[TProperties, References],
    _BM25Generate[TProperties, References],
    _FetchObjectsGenerate[TProperties, References],
    _FetchObjectsByIDsGenerate[TProperties, References],
    _HybridGenerate[TProperties, References],
    _NearImageGenerate[TProperties, References],
    _NearMediaGenerate[TProperties, References],
    _NearObjectGenerate[TProperties, References],
    _NearTextGenerate[TProperties, References],
    _NearVectorGenerate[TProperties, References],
):
    pass

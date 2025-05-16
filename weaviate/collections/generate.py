from typing import Generic

from weaviate.collections.classes.types import References, TProperties
from weaviate.collections.queries.bm25 import _BM25Generate, _BM25GenerateAsync
from weaviate.collections.queries.fetch_objects import (
    _FetchObjectsGenerate,
    _FetchObjectsGenerateAsync,
)
from weaviate.collections.queries.fetch_objects_by_ids import (
    _FetchObjectsByIDsGenerate,
    _FetchObjectsByIDsGenerateAsync,
)
from weaviate.collections.queries.hybrid import _HybridGenerate, _HybridGenerateAsync
from weaviate.collections.queries.near_image import (
    _NearImageGenerate,
    _NearImageGenerateAsync,
)
from weaviate.collections.queries.near_media import (
    _NearMediaGenerate,
    _NearMediaGenerateAsync,
)
from weaviate.collections.queries.near_object import (
    _NearObjectGenerate,
    _NearObjectGenerateAsync,
)
from weaviate.collections.queries.near_text import (
    _NearTextGenerate,
    _NearTextGenerateAsync,
)
from weaviate.collections.queries.near_vector import (
    _NearVectorGenerate,
    _NearVectorGenerateAsync,
)


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

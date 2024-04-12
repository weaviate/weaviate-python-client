from typing import Generic

from weaviate.collections.classes.types import TProperties, References

from weaviate.collections.queries.bm25 import _BM25Generate
from weaviate.collections.queries.fetch_objects import _FetchObjectsGenerate
from weaviate.collections.queries.hybrid import _HybridGenerate
from weaviate.collections.queries.near_image import _NearImageGenerate
from weaviate.collections.queries.near_media import _NearMediaGenerate
from weaviate.collections.queries.near_object import _NearObjectGenerate
from weaviate.collections.queries.near_text import _NearTextGenerate
from weaviate.collections.queries.near_vector import _NearVectorGenerate


class _GenerateCollection(
    Generic[TProperties, References],
    _BM25Generate[TProperties, References],
    _FetchObjectsGenerate[TProperties, References],
    _HybridGenerate[TProperties, References],
    _NearImageGenerate[TProperties, References],
    _NearMediaGenerate[TProperties, References],
    _NearObjectGenerate[TProperties, References],
    _NearTextGenerate[TProperties, References],
    _NearVectorGenerate[TProperties, References],
):
    pass

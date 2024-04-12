from typing import Generic

from weaviate.collections.classes.types import TProperties, References

from weaviate.collections.queries.bm25 import _BM25GenerateAsync
from weaviate.collections.queries.fetch_objects import _FetchObjectsGenerateAsync
from weaviate.collections.queries.hybrid import _HybridGenerateAsync
from weaviate.collections.queries.near_image import _NearImageGenerateAsync
from weaviate.collections.queries.near_media import _NearMediaGenerateAsync
from weaviate.collections.queries.near_object import _NearObjectGenerateAsync
from weaviate.collections.queries.near_text import _NearTextGenerateAsync
from weaviate.collections.queries.near_vector import _NearVectorGenerateAsync


class _GenerateCollectionAsync(
    Generic[TProperties, References],
    _BM25GenerateAsync[TProperties, References],
    _FetchObjectsGenerateAsync[TProperties, References],
    _HybridGenerateAsync[TProperties, References],
    _NearImageGenerateAsync[TProperties, References],
    _NearMediaGenerateAsync[TProperties, References],
    _NearObjectGenerateAsync[TProperties, References],
    _NearTextGenerateAsync[TProperties, References],
    _NearVectorGenerateAsync[TProperties, References],
):
    pass

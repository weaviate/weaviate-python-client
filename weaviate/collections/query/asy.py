from typing import Generic

from weaviate.collections.classes.types import TProperties, References

from weaviate.collections.queries.bm25 import _BM25QueryAsync
from weaviate.collections.queries.fetch_object_by_id import _FetchObjectByIDQueryAsync
from weaviate.collections.queries.fetch_objects import _FetchObjectsQueryAsync
from weaviate.collections.queries.hybrid import _HybridQueryAsync
from weaviate.collections.queries.near_image import _NearImageQueryAsync
from weaviate.collections.queries.near_media import _NearMediaQueryAsync
from weaviate.collections.queries.near_object import _NearObjectQueryAsync
from weaviate.collections.queries.near_text import _NearTextQueryAsync
from weaviate.collections.queries.near_vector import _NearVectorQueryAsync


class _QueryCollectionAsync(
    Generic[TProperties, References],
    _BM25QueryAsync[TProperties, References],
    _FetchObjectByIDQueryAsync[TProperties, References],
    _FetchObjectsQueryAsync[TProperties, References],
    _HybridQueryAsync[TProperties, References],
    _NearImageQueryAsync[TProperties, References],
    _NearMediaQueryAsync[TProperties, References],
    _NearObjectQueryAsync[TProperties, References],
    _NearTextQueryAsync[TProperties, References],
    _NearVectorQueryAsync[TProperties, References],
):
    pass

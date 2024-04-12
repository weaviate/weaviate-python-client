from typing import Generic

from weaviate.collections.classes.types import TProperties, References

from weaviate.collections.queries.bm25 import _BM25Query
from weaviate.collections.queries.fetch_object_by_id import _FetchObjectByIDQuery
from weaviate.collections.queries.fetch_objects import _FetchObjectsQuery
from weaviate.collections.queries.hybrid import _HybridQuery
from weaviate.collections.queries.near_image import _NearImageQuery
from weaviate.collections.queries.near_media import _NearMediaQuery
from weaviate.collections.queries.near_object import _NearObjectQuery
from weaviate.collections.queries.near_text import _NearTextQuery
from weaviate.collections.queries.near_vector import _NearVectorQuery


class _QueryCollection(
    Generic[TProperties, References],
    _BM25Query[TProperties, References],
    _FetchObjectByIDQuery[TProperties, References],
    _FetchObjectsQuery[TProperties, References],
    _HybridQuery[TProperties, References],
    _NearImageQuery[TProperties, References],
    _NearMediaQuery[TProperties, References],
    _NearObjectQuery[TProperties, References],
    _NearTextQuery[TProperties, References],
    _NearVectorQuery[TProperties, References],
):
    pass

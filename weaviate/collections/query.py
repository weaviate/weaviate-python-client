from typing import Generic

from weaviate.collections.classes.types import TProperties, References

from weaviate.collections.queries.bm25 import _BM25QueryAsync, _BM25Query
from weaviate.collections.queries.fetch_object_by_id import (
    _FetchObjectByIDQueryAsync,
    _FetchObjectByIDQuery,
)
from weaviate.collections.queries.fetch_objects_by_ids import (
    _FetchObjectsByIDsQueryAsync,
    _FetchObjectsByIDsQuery,
)
from weaviate.collections.queries.fetch_objects import _FetchObjectsQueryAsync, _FetchObjectsQuery
from weaviate.collections.queries.hybrid import _HybridQueryAsync, _HybridQuery
from weaviate.collections.queries.near_image import _NearImageQueryAsync, _NearImageQuery
from weaviate.collections.queries.near_media import _NearMediaQueryAsync, _NearMediaQuery
from weaviate.collections.queries.near_object import _NearObjectQueryAsync, _NearObjectQuery
from weaviate.collections.queries.near_text import _NearTextQueryAsync, _NearTextQuery
from weaviate.collections.queries.near_vector import _NearVectorQueryAsync, _NearVectorQuery


class _QueryCollectionAsync(
    Generic[TProperties, References],
    _BM25QueryAsync[TProperties, References],
    _FetchObjectByIDQueryAsync[TProperties, References],
    _FetchObjectsByIDsQueryAsync[TProperties, References],
    _FetchObjectsQueryAsync[TProperties, References],
    _HybridQueryAsync[TProperties, References],
    _NearImageQueryAsync[TProperties, References],
    _NearMediaQueryAsync[TProperties, References],
    _NearObjectQueryAsync[TProperties, References],
    _NearTextQueryAsync[TProperties, References],
    _NearVectorQueryAsync[TProperties, References],
):
    pass


class _QueryCollection(
    Generic[TProperties, References],
    _BM25Query[TProperties, References],
    _FetchObjectByIDQuery[TProperties, References],
    _FetchObjectsByIDsQuery[TProperties, References],
    _FetchObjectsQuery[TProperties, References],
    _HybridQuery[TProperties, References],
    _NearImageQuery[TProperties, References],
    _NearMediaQuery[TProperties, References],
    _NearObjectQuery[TProperties, References],
    _NearTextQuery[TProperties, References],
    _NearVectorQuery[TProperties, References],
):
    pass

from typing import Generic

from weaviate.collections.classes.types import References, TProperties
from weaviate.collections.queries.bm25 import _BM25Query, _BM25QueryAsync
from weaviate.collections.queries.fetch_object_by_id import (
    _FetchObjectByIDQuery,
    _FetchObjectByIDQueryAsync,
)
from weaviate.collections.queries.fetch_objects import (
    _FetchObjectsQuery,
    _FetchObjectsQueryAsync,
)
from weaviate.collections.queries.fetch_objects_by_ids import (
    _FetchObjectsByIDsQuery,
    _FetchObjectsByIDsQueryAsync,
)
from weaviate.collections.queries.hybrid import _HybridQuery, _HybridQueryAsync
from weaviate.collections.queries.near_image import (
    _NearImageQuery,
    _NearImageQueryAsync,
)
from weaviate.collections.queries.near_media import (
    _NearMediaQuery,
    _NearMediaQueryAsync,
)
from weaviate.collections.queries.near_object import (
    _NearObjectQuery,
    _NearObjectQueryAsync,
)
from weaviate.collections.queries.near_text import _NearTextQuery, _NearTextQueryAsync
from weaviate.collections.queries.near_vector import (
    _NearVectorQuery,
    _NearVectorQueryAsync,
)


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

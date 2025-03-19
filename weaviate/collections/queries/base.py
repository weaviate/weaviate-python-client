from typing import Generic, Optional, Type

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import (
    CrossReferences,
    WeaviateProperties,
    CrossReferences,
)
from weaviate.connect.v4 import ConnectionType

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_object_by_id.executor import _FetchObjectsByIdQueryExecutor
from weaviate.collections.queries.fetch_objects.executors import (
    _FetchObjectsGenerateExecutor,
    _FetchObjectsQueryExecutor,
)
from weaviate.collections.queries.bm25.executors import _BM25GenerateExecutor, _BM25QueryExecutor
from weaviate.collections.queries.hybrid.executors import (
    _HybridGenerateExecutor,
    _HybridQueryExecutor,
)
from weaviate.collections.queries.near_image.executors import (
    _NearImageGenerateExecutor,
    _NearImageQueryExecutor,
)
from weaviate.collections.queries.near_media.executors import (
    _NearMediaGenerateExecutor,
    _NearMediaQueryExecutor,
)
from weaviate.collections.queries.near_object.executors import (
    _NearObjectGenerateExecutor,
    _NearObjectQueryExecutor,
)
from weaviate.collections.queries.near_text.executors import (
    _NearTextGenerateExecutor,
    _NearTextQueryExecutor,
)
from weaviate.collections.queries.near_vector.executors import (
    _NearVectorGenerateExecutor,
    _NearVectorQueryExecutor,
)


class _GenerateExecutor(
    Generic[Properties, References],
    _FetchObjectsGenerateExecutor[Properties, References],
    _BM25GenerateExecutor[Properties, References],
    _HybridGenerateExecutor[Properties, References],
    _NearImageGenerateExecutor[Properties, References],
    _NearMediaGenerateExecutor[Properties, References],
    _NearObjectGenerateExecutor[Properties, References],
    _NearTextGenerateExecutor[Properties, References],
    _NearVectorGenerateExecutor[Properties, References],
):
    pass


class _QueryExecutor(
    Generic[Properties, References],
    _FetchObjectsByIdQueryExecutor[Properties, References],
    _FetchObjectsQueryExecutor[Properties, References],
    _BM25QueryExecutor[Properties, References],
    _HybridQueryExecutor[Properties, References],
    _NearImageQueryExecutor[Properties, References],
    _NearMediaQueryExecutor[Properties, References],
    _NearObjectQueryExecutor[Properties, References],
    _NearTextQueryExecutor[Properties, References],
    _NearVectorQueryExecutor[Properties, References],
):
    pass


class _BaseGenerate(Generic[ConnectionType, Properties, References]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        properties: Optional[Type[Properties]],
        references: Optional[Type[References]],
        validate_arguments: bool,
    ):
        self._connection = connection
        self._executor = _GenerateExecutor[Properties, References](
            connection._weaviate_version,
            name,
            consistency_level,
            tenant,
            properties,
            references,
            validate_arguments,
        )


class _BaseQuery(Generic[ConnectionType, Properties, References]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        properties: Optional[Type[Properties]],
        references: Optional[Type[References]],
        validate_arguments: bool,
    ):
        self._connection = connection
        self._executor = _QueryExecutor[Properties, References](
            connection._weaviate_version,
            name,
            consistency_level,
            tenant,
            properties,
            references,
            validate_arguments,
        )

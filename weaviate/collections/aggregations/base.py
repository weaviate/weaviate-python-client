from typing import Generic, Optional
from weaviate.collections.aggregations.executors.hybrid import _HybridExecutor
from weaviate.collections.aggregations.executors.near_image import _NearImageExecutor
from weaviate.collections.aggregations.executors.near_object import _NearObjectExecutor
from weaviate.collections.aggregations.executors.near_text import _NearTextExecutor
from weaviate.collections.aggregations.executors.near_vector import _NearVectorExecutor
from weaviate.collections.aggregations.executors.over_all import _OverAllExecutor
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect.v4 import ConnectionType


class _AggregateExecutor(
    _HybridExecutor,
    _NearImageExecutor,
    _NearObjectExecutor,
    _NearTextExecutor,
    _NearVectorExecutor,
    _OverAllExecutor,
):
    pass


class _BaseAggregate(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        validate_arguments: bool,
    ):
        self._connection: ConnectionType = connection
        self._executor = _AggregateExecutor(
            connection._weaviate_version,
            name,
            consistency_level,
            tenant,
            validate_arguments,
        )

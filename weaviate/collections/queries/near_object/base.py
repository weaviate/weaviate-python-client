from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.executors import (
    _NearObjectGenerateExecutor,
    _NearObjectQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _NearObjectGenerateBase(
    Generic[ConnectionType, Properties, References],
    _NearObjectGenerateExecutor[Properties, References],
):
    pass


class _NearObjectQueryBase(
    Generic[ConnectionType, Properties, References],
    _NearObjectQueryExecutor[Properties, References],
):
    pass

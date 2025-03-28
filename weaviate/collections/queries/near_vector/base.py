from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.executors import (
    _NearVectorGenerateExecutor,
    _NearVectorQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _NearVectorGenerateBase(
    Generic[ConnectionType, Properties, References],
    _NearVectorGenerateExecutor[Properties, References],
):
    pass


class _NearVectorQueryBase(
    Generic[ConnectionType, Properties, References],
    _NearVectorQueryExecutor[Properties, References],
):
    pass

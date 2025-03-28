from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.executors import (
    _NearTextGenerateExecutor,
    _NearTextQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _NearTextGenerateBase(
    Generic[ConnectionType, Properties, References],
    _NearTextGenerateExecutor[Properties, References],
):
    pass


class _NearTextQueryBase(
    Generic[ConnectionType, Properties, References],
    _NearTextQueryExecutor[Properties, References],
):
    pass

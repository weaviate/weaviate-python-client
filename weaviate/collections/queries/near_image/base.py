from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.executors import (
    _NearImageGenerateExecutor,
    _NearImageQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _NearImageGenerateBase(
    Generic[ConnectionType, Properties, References],
    _NearImageGenerateExecutor[Properties, References],
):
    pass


class _NearImageQueryBase(
    Generic[ConnectionType, Properties, References],
    _NearImageQueryExecutor[Properties, References],
):
    pass

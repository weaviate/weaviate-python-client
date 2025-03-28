from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.executors import (
    _NearMediaGenerateExecutor,
    _NearMediaQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _NearMediaGenerateBase(
    Generic[ConnectionType, Properties, References],
    _NearMediaGenerateExecutor[Properties, References],
):
    pass


class _NearMediaQueryBase(
    Generic[ConnectionType, Properties, References],
    _NearMediaQueryExecutor[Properties, References],
):
    pass

from typing import Generic

from weaviate.collections.aggregations.near_image.executor import _NearImageExecutor
from weaviate.connect.v4 import ConnectionType


class _NearImageBase(Generic[ConnectionType], _NearImageExecutor):
    pass

from typing import Generic

from weaviate.collections.aggregations.near_object.executor import _NearObjectExecutor
from weaviate.connect.v4 import ConnectionType


class _NearObjectBase(Generic[ConnectionType], _NearObjectExecutor):
    pass

from typing import Generic

from weaviate.collections.aggregations.near_vector.executor import _NearVectorExecutor
from weaviate.connect.v4 import ConnectionType


class _NearVectorBase(Generic[ConnectionType], _NearVectorExecutor):
    pass

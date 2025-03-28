from typing import Generic

from weaviate.collections.aggregations.near_text.executor import _NearTextExecutor
from weaviate.connect.v4 import ConnectionType


class _NearTextBase(Generic[ConnectionType], _NearTextExecutor):
    pass

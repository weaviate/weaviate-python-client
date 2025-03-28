from typing import Generic

from weaviate.collections.aggregations.over_all.executor import _OverAllExecutor
from weaviate.connect.v4 import ConnectionType


class _OverAllBase(Generic[ConnectionType], _OverAllExecutor):
    pass

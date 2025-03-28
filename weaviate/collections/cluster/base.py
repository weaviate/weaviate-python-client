from typing import Generic

from weaviate.collections.cluster.executor import _ClusterExecutor
from weaviate.connect.v4 import ConnectionType


class _ClusterBase(Generic[ConnectionType], _ClusterExecutor):
    def __init__(self, connection: ConnectionType):
        super().__init__(connection)

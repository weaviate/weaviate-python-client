from typing import Generic, Optional

from weaviate.collections.config.executor import _ConfigExecutor
from weaviate.connect.v4 import ConnectionType


class _ConfigCollectionBase(Generic[ConnectionType], _ConfigExecutor):
    def __init__(self, connection: ConnectionType, name: str, tenant: Optional[str]) -> None:
        super().__init__(connection, name, tenant)

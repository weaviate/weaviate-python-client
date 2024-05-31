from typing import Optional
from weaviate.connect import ConnectionV4


class _ConfigCollectionBase:
    def __init__(self, connection: ConnectionV4, name: str, tenant: Optional[str]) -> None:
        self._connection = connection
        self._name = name
        self._tenant = tenant

from typing import Generic

from weaviate.connect.v4 import ConnectionType
from weaviate.users.executor import _DeprecatedExecutor, _DBExecutor, _OIDCExecutor


class _UsersOIDCBase(Generic[ConnectionType], _OIDCExecutor):
    def __init__(self, connection: ConnectionType) -> None:
        super().__init__(connection)


class _UsersDBBase(Generic[ConnectionType], _DBExecutor):
    def __init__(self, connection: ConnectionType) -> None:
        super().__init__(connection)


class _UsersBase(Generic[ConnectionType], _DeprecatedExecutor):
    def __init__(self, connection: ConnectionType) -> None:
        super().__init__(connection)

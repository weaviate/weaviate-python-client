from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.users.executor import (
    _DeprecatedExecutor,
    _DBExecutor,
    _OIDCExecutor,
)


@executor.wrap("async")
class _UsersDBAsync(_DBExecutor[ConnectionAsync]):
    pass


@executor.wrap("async")
class _UsersOIDCAsync(_OIDCExecutor[ConnectionAsync]):
    pass


@executor.wrap("async")
class _UsersAsync(_DeprecatedExecutor[ConnectionAsync]):
    def __init__(self, connection: ConnectionAsync):
        super().__init__(connection)
        self.db = _UsersDBAsync(connection)
        self.oidc = _UsersOIDCAsync(connection)

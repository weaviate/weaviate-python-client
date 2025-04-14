from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.executor import (
    _DeprecatedExecutor,
    _DBExecutor,
    _OIDCExecutor,
)


@executor.wrap("sync")
class _UsersDB(_DBExecutor[ConnectionSync]):
    pass


@executor.wrap("sync")
class _UsersOIDC(_OIDCExecutor[ConnectionSync]):
    pass


@executor.wrap("sync")
class _Users(_DeprecatedExecutor[ConnectionSync]):
    def __init__(self, connection: ConnectionSync):
        super().__init__(connection)
        self.db = _UsersDB(connection)
        self.oidc = _UsersOIDC(connection)

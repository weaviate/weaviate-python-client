from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.executor import (
    _UsersExecutor,
    _UsersDBExecutor,
    _UsersOIDCExecutor,
)


@executor.wrap("sync")
class _UsersDB(_UsersDBExecutor[ConnectionSync]):
    pass


@executor.wrap("sync")
class _UsersOIDC(_UsersOIDCExecutor[ConnectionSync]):
    pass


@executor.wrap("sync")
class _Users(_UsersExecutor[ConnectionSync]):
    def __init__(self, connection: ConnectionSync):
        super().__init__(connection)
        self.db = _UsersDB(connection)
        self.oidc = _UsersOIDC(connection)

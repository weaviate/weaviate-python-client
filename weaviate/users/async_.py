from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.users.executor import (
    _UsersExecutor,
    _UsersDBExecutor,
    _UsersOIDCExecutor,
)


@executor.wrap("async")
class _UsersDBAsync(_UsersDBExecutor[ConnectionAsync]):
    pass


@executor.wrap("async")
class _UsersOIDCAsync(_UsersOIDCExecutor[ConnectionAsync]):
    pass


@executor.wrap("async")
class _UsersAsync(_UsersExecutor[ConnectionAsync]):
    def __init__(self, connection: ConnectionAsync):
        super().__init__(connection)
        self.db = _UsersDBAsync(connection)
        self.oidc = _UsersOIDCAsync(connection)

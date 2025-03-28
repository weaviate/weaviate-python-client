from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.base import (
    _UsersBase,
    _UsersDBBase,
    _UsersOIDCBase,
)


@executor.wrap("sync")
class _UsersDB(_UsersDBBase[ConnectionSync]):
    pass


@executor.wrap("sync")
class _UsersOIDC(_UsersOIDCBase[ConnectionSync]):
    pass


@executor.wrap("sync")
class _Users(_UsersBase[ConnectionSync]):
    def __init__(self, connection: ConnectionSync):
        super().__init__(connection)
        self.db = _UsersDB(connection)
        self.oidc = _UsersOIDC(connection)

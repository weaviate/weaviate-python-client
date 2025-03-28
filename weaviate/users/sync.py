from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.base import (
    _UsersBase,
    _UsersDBBase,
    _UsersOIDCBase,
)


@impl.wrap("sync")
class _UsersDB(_UsersDBBase[ConnectionSync]):
    pass


@impl.wrap("sync")
class _UsersOIDC(_UsersOIDCBase[ConnectionSync]):
    pass


@impl.wrap("sync")
class _Users(_UsersBase[ConnectionSync]):
    def __init__(self, connection: ConnectionSync):
        super().__init__(connection)
        self.db = _UsersDB(connection)
        self.oidc = _UsersOIDC(connection)

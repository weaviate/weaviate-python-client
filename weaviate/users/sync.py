from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.base import (
    _UsersBase,
    _UsersDBBase,
    _UsersOIDCBase,
)


@impl.generate("sync")
class _UsersDB(_UsersDBBase[ConnectionSync]):
    pass


@impl.generate("sync")
class _UsersOIDC(_UsersOIDCBase[ConnectionSync]):
    pass


@impl.generate("sync")
class _Users(_UsersBase[ConnectionSync]):
    def __init__(self, connection):
        super().__init__(connection)
        self.db = _UsersDB(self._connection)
        self.oidc = _UsersOIDC(self._connection)

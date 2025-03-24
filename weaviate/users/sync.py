from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.async_ import (
    _UsersBase,
    _UsersAsync,
    _UsersDBBase,
    _UsersDBAsync,
    _UsersOIDCBase,
    _UsersOIDCAsync,
)


@syncify.convert_new(_UsersDBAsync)
class _UsersDB(_UsersDBBase[ConnectionSync]):
    pass


@syncify.convert_new(_UsersOIDCAsync)
class _UsersOIDC(_UsersOIDCBase[ConnectionSync]):
    pass


@syncify.convert_new(_UsersAsync)
class _Users(_UsersBase[ConnectionSync]):
    def __init__(self, connection):
        super().__init__(connection)
        self.db = _UsersDB(self._connection)
        self.oidc = _UsersOIDC(self._connection)

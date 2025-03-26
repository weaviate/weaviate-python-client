from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.users.base import (
    _UsersBase,
    _UsersDBBase,
    _UsersOIDCBase,
)


@impl.generate("async")
class _UsersDBAsync(_UsersDBBase[ConnectionAsync]):
    pass


@impl.generate("async")
class _UsersOIDCAsync(_UsersOIDCBase[ConnectionAsync]):
    pass


@impl.generate("async")
class _UsersAsync(_UsersBase[ConnectionAsync]):
    def __init__(self, connection):
        super().__init__(connection)
        self.db = _UsersDBAsync(self._connection)
        self.oidc = _UsersOIDCAsync(self._connection)

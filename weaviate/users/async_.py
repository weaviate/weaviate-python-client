from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.users.base import (
    _UsersBase,
    _UsersDBBase,
    _UsersOIDCBase,
)


@impl.wrap("async")
class _UsersDBAsync(_UsersDBBase[ConnectionAsync]):
    pass


@impl.wrap("async")
class _UsersOIDCAsync(_UsersOIDCBase[ConnectionAsync]):
    pass


@impl.wrap("async")
class _UsersAsync(_UsersBase[ConnectionAsync]):
    def __init__(self, connection: ConnectionAsync):
        super().__init__(connection)
        self.db = _UsersDBAsync(connection)
        self.oidc = _UsersOIDCAsync(connection)

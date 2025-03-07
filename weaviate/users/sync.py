from weaviate import syncify

from weaviate.users.users import _UsersAsync, _UserDBAsync, _UserOIDCAsync


@syncify.convert
class _UsersDB(_UserDBAsync):
    pass


@syncify.convert
class _UsersOIDC(_UserOIDCAsync):
    pass


@syncify.convert
class _Users(_UsersAsync):
    def __init__(self, connection):
        super().__init__(connection)
        self.db = _UsersDB(self._connection)
        self.oidc = _UsersOIDC(self._connection)

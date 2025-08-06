from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.groups.base import _BaseExecutor, _GroupsOIDCExecutor


@executor.wrap("sync")
class _GroupsOIDC(_GroupsOIDCExecutor[ConnectionSync]):
    pass


@executor.wrap("sync")
class _Groups(_BaseExecutor[ConnectionSync]):
    def __init__(self, connection: ConnectionSync):
        self.oidc = _GroupsOIDC(connection)

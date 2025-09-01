from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.groups.base import _GroupsOIDCExecutor


@executor.wrap("async")
class _GroupsAsync:
    def __init__(self, connection: ConnectionAsync):
        self.oidc = _GroupsOIDCAsync(connection)


@executor.wrap("sync")
class _GroupsOIDCAsync(_GroupsOIDCExecutor[ConnectionAsync]):
    pass

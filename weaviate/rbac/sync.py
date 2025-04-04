from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.rbac.executor import _RolesExecutor


@executor.wrap("sync")
class _Roles(_RolesExecutor[ConnectionSync]):
    pass

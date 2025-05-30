from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.rbac.executor import _RolesExecutor


@executor.wrap("async")
class _RolesAsync(_RolesExecutor[ConnectionAsync]):
    pass

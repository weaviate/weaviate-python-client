from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.rbac.base import _RolesBase


@executor.wrap("sync")
class _Roles(_RolesBase[ConnectionSync]):
    pass

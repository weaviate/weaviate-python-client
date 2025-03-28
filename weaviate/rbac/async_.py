from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.rbac.base import _RolesBase


@executor.wrap("async")
class _RolesAsync(_RolesBase[ConnectionAsync]):
    pass

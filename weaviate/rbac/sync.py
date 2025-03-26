from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.rbac.base import _RolesBase


@impl.generate("sync")
class _Roles(_RolesBase[ConnectionSync]):
    pass

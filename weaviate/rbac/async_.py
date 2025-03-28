from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.rbac.base import _RolesBase


@impl.wrap("async")
class _RolesAsync(_RolesBase[ConnectionAsync]):
    pass

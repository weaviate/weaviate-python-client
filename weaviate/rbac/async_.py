from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.rbac.base import _RolesBase


@impl.generate("async")
class _RolesAsync(_RolesBase[ConnectionAsync]):
    pass

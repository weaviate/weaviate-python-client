from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.rbac.async_ import _RolesAsync, _RolesBase


@syncify.convert(_RolesAsync)
class _Roles(_RolesBase[ConnectionSync]):
    pass

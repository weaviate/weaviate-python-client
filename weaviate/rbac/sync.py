from weaviate import syncify
from weaviate.rbac.roles import _RolesAsync


@syncify.convert
class _Roles(_RolesAsync):
    pass

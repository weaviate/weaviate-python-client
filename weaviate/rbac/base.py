from typing import Generic
from weaviate.connect.v4 import ConnectionType
from weaviate.rbac.executor import _RolesExecutor


class _RolesBase(Generic[ConnectionType], _RolesExecutor):
    pass

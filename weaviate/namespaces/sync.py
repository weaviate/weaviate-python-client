from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.namespaces.base import _NamespacesExecutor


@executor.wrap("sync")
class _Namespaces(_NamespacesExecutor[ConnectionSync]):
    pass

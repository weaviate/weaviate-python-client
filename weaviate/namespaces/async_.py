from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.namespaces.base import _NamespacesExecutor


@executor.wrap("async")
class _NamespacesAsync(_NamespacesExecutor[ConnectionAsync]):
    pass

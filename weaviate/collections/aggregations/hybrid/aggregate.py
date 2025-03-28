from weaviate.connect import impl
from weaviate.collections.aggregations.hybrid.base import _HybridBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _HybridAsync(_HybridBase[ConnectionAsync]):
    pass


@impl.wrap("sync")
class _Hybrid(_HybridBase[ConnectionSync]):
    pass

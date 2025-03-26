from weaviate.connect import impl
from weaviate.collections.aggregations.hybrid.base import _HybridBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _HybridAsync(_HybridBase[ConnectionAsync]):
    pass


@impl.generate("sync")
class _Hybrid(_HybridBase[ConnectionSync]):
    pass

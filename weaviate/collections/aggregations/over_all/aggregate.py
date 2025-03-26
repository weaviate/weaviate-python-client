from weaviate.connect import impl
from weaviate.collections.aggregations.over_all.base import _OverAllBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _OverAllAsync(_OverAllBase[ConnectionAsync]):
    pass


@impl.generate("sync")
class _OverAll(_OverAllBase[ConnectionSync]):
    pass

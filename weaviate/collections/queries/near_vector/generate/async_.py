from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.generate.executor import _NearVectorGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearVectorGenerateAsync(
    Generic[Properties, References],
    _NearVectorGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass

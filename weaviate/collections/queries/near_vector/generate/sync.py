from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.generate.executor import _NearVectorGenerateExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearVectorGenerate(
    Generic[Properties, References],
    _NearVectorGenerateExecutor[ConnectionSync, Properties, References],
):
    pass

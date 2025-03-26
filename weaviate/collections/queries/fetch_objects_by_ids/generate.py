from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.base import _FetchObjectsByIDsGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _FetchObjectsByIDsGenerateAsync(
    Generic[Properties, References],
    _FetchObjectsByIDsGenerateBase[ConnectionAsync, Properties, References],
):
    pass


@impl.generate("sync")
class _FetchObjectsByIDsGenerate(
    Generic[Properties, References],
    _FetchObjectsByIDsGenerateBase[ConnectionSync, Properties, References],
):
    pass

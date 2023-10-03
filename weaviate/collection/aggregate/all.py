from typing import Generic

from weaviate.collection.aggregate.base import _Aggregate
from weaviate.collection.classes.types import Properties


class _All(Generic[Properties], _Aggregate[Properties]):
    pass

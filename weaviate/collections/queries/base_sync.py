from typing import Generic, TYPE_CHECKING

from weaviate.collections.classes.types import (
    Properties,
    References,
)

if TYPE_CHECKING:
    from weaviate.collections.generate.asy import _GenerateCollectionAsync
    from weaviate.collections.query.asy import _QueryCollectionAsync
from weaviate.event_loop import _EventLoop


class _BaseQuery(Generic[Properties, References]):
    _loop: _EventLoop
    _query: "_QueryCollectionAsync[Properties, References]"

    def __init__(self, loop: _EventLoop, query: "_QueryCollectionAsync[Properties, References]"):
        self._loop = loop
        self._query = query


class _BaseGenerate(Generic[Properties, References]):
    _loop: _EventLoop
    _generate: "_GenerateCollectionAsync[Properties, References]"

    def __init__(
        self, loop: _EventLoop, generate: "_GenerateCollectionAsync[Properties, References]"
    ):
        self._loop = loop
        self._generate = generate

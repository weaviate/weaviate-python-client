from dataclasses import dataclass
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
)
from uuid import UUID

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import METADATA
from weaviate.collections.classes.internal import (
    Object,
    ReturnProperties,
    ReturnReferences,
    TProperties,
    TReferences,
)
from weaviate.collections.queries.fetch_objects import (
    _FetchObjectsQuery,
    _FetchObjectsQueryAsync,
)
from weaviate.types import UUID as UUIDorStr

ITERATOR_CACHE_SIZE = 100


@dataclass
class _IteratorInputs(Generic[TProperties, TReferences]):
    filters: Optional[_Filters]
    include_vector: bool
    return_metadata: Optional[METADATA]
    return_properties: Optional[ReturnProperties[TProperties]]
    return_references: Optional[ReturnReferences[TReferences]]
    after: Optional[UUIDorStr]


def _parse_after(after: Optional[UUIDorStr]) -> UUIDorStr:
    if after is None:
        return ""

    return UUID(after) if not isinstance(after, UUID) else after


class _ObjectIterator(
    Generic[TProperties, TReferences],
    Iterable[Object[TProperties, TReferences]],
):
    def __init__(
        self,
        query: _FetchObjectsQuery[Any, Any],
        inputs: _IteratorInputs[TProperties, TReferences],
        cache_size: Optional[int] = None,
    ) -> None:
        self.__query = query
        self.__inputs = inputs

        self.__iter_object_cache: List[Object[TProperties, TReferences]] = []
        self.__iter_object_last_uuid: Optional[UUIDorStr] = _parse_after(self.__inputs.after)
        self.__iter_cache_size = cache_size or ITERATOR_CACHE_SIZE
        self.__iter_shard_cursors: Optional[Dict[str, str]] = None

    def __iter__(
        self,
    ) -> Iterator[Object[TProperties, TReferences]]:
        self.__iter_object_cache = []
        self.__iter_object_last_uuid = _parse_after(self.__inputs.after)
        self.__iter_shard_cursors = None
        return self

    def __next__(self) -> Object[TProperties, TReferences]:
        if len(self.__iter_object_cache) == 0:
            # Shard cursor pagination:
            # - First call uses shard_cursors=None; subsequent calls include the cursors
            #   returned by the server in the previous SearchReply.
            # - The server returns updated shard_cursors in each response, which are fed
            #   back into the next request so each shard resumes from the right position.
            # - Iteration ends when the server returns an empty result set.
            res = self.__query.fetch_objects(
                limit=self.__iter_cache_size,
                after=self.__iter_object_last_uuid,
                include_vector=self.__inputs.include_vector,
                return_metadata=self.__inputs.return_metadata,
                return_properties=self.__inputs.return_properties,
                return_references=self.__inputs.return_references,
                filters=self.__inputs.filters,
                shard_cursors=self.__iter_shard_cursors,
            )
            self.__iter_object_cache = res.objects  # type: ignore
            self.__iter_shard_cursors = res.shard_cursors
            if len(self.__iter_object_cache) == 0:
                raise StopIteration

        ret_object = self.__iter_object_cache.pop(0)
        self.__iter_object_last_uuid = ret_object.uuid
        assert (
            self.__iter_object_last_uuid is not None
        )  # if this is None the iterator will never stop
        return ret_object  # pyright: ignore


class _ObjectAIterator(
    Generic[TProperties, TReferences],
    AsyncIterable[Object[TProperties, TReferences]],
):
    def __init__(
        self,
        query: _FetchObjectsQueryAsync[Any, Any],
        inputs: _IteratorInputs[TProperties, TReferences],
        cache_size: Optional[int] = None,
    ) -> None:
        self.__query = query
        self.__inputs = inputs

        self.__iter_object_cache: List[Object[TProperties, TReferences]] = []
        self.__iter_object_last_uuid: UUIDorStr = _parse_after(self.__inputs.after)
        self.__iter_cache_size = cache_size or ITERATOR_CACHE_SIZE
        self.__iter_shard_cursors: Optional[Dict[str, str]] = None

    def __aiter__(
        self,
    ) -> AsyncIterator[Object[TProperties, TReferences]]:
        self.__iter_object_cache = []
        self.__iter_object_last_uuid = _parse_after(self.__inputs.after)
        self.__iter_shard_cursors = None
        return self

    async def __anext__(
        self,
    ) -> Object[TProperties, TReferences]:
        if len(self.__iter_object_cache) == 0:
            # Shard cursor pagination:
            # - First call uses shard_cursors=None; subsequent calls include the cursors
            #   returned by the server in the previous SearchReply.
            # - The server returns updated shard_cursors in each response, which are fed
            #   back into the next request so each shard resumes from the right position.
            # - Iteration ends when the server returns an empty result set.
            res = await self.__query.fetch_objects(
                limit=self.__iter_cache_size,
                after=self.__iter_object_last_uuid,
                include_vector=self.__inputs.include_vector,
                return_metadata=self.__inputs.return_metadata,
                return_properties=self.__inputs.return_properties,
                return_references=self.__inputs.return_references,
                filters=self.__inputs.filters,
                shard_cursors=self.__iter_shard_cursors,
            )
            self.__iter_object_cache = res.objects  # type: ignore
            self.__iter_shard_cursors = res.shard_cursors
            if len(self.__iter_object_cache) == 0:
                raise StopAsyncIteration

        ret_object = self.__iter_object_cache.pop(0)
        self.__iter_object_last_uuid = ret_object.uuid
        assert (
            self.__iter_object_last_uuid is not None
        )  # if this is None the iterator will never stop
        return ret_object  # pyright: ignore

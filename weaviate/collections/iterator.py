from typing import Callable, Generic, Iterable, Iterator, List, Optional, Union
from uuid import UUID

from weaviate.collections.classes.internal import CrossReferences, Object
from weaviate.collections.classes.types import (
    P,
    R,
    V,
    Properties,
    TProperties,
    References,
    TReferences,
    Vectors,
)


ITERATOR_CACHE_SIZE = 100


class _ObjectIterator(Generic[P, R, V], Iterable[Object[P, R, V]]):
    def __init__(
        self, fetch_objects_query: Callable[[int, Optional[UUID]], List[Object[P, R, V]]]
    ) -> None:
        self.__query = fetch_objects_query

        self.__iter_object_cache: List[Object[P, R, V]] = []
        self.__iter_object_last_uuid: Optional[UUID] = None

    def __iter__(self) -> Iterator[Object[P, R, V]]:
        self.__iter_object_cache = []
        self.__iter_object_last_uuid = None
        return self

    def __next__(self) -> Object[P, R, V]:
        if len(self.__iter_object_cache) == 0:
            objects = self.__query(
                ITERATOR_CACHE_SIZE,
                self.__iter_object_last_uuid,
            )
            self.__iter_object_cache = objects
            if len(self.__iter_object_cache) == 0:
                raise StopIteration

        ret_object = self.__iter_object_cache.pop(0)
        self.__iter_object_last_uuid = ret_object.uuid
        assert (
            self.__iter_object_last_uuid is not None
        )  # if this is None the iterator will never stop
        return ret_object


ObjectIterator = Union[
    _ObjectIterator[Properties, References, None],
    _ObjectIterator[Properties, References, Vectors],
    _ObjectIterator[TProperties, References, None],
    _ObjectIterator[TProperties, References, Vectors],
    _ObjectIterator[Properties, CrossReferences, None],
    _ObjectIterator[Properties, CrossReferences, Vectors],
    _ObjectIterator[Properties, TReferences, None],
    _ObjectIterator[Properties, TReferences, Vectors],
    _ObjectIterator[TProperties, CrossReferences, None],
    _ObjectIterator[TProperties, CrossReferences, Vectors],
    _ObjectIterator[TProperties, TReferences, None],
    _ObjectIterator[TProperties, TReferences, Vectors],
]

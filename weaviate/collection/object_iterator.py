from typing import Generic, Iterable, Iterator, List, Optional, Type, Union
from uuid import UUID

from weaviate.collection.classes.grpc import MetadataQuery, PROPERTIES
from weaviate.collection.classes.internal import _Object, _QueryReturn
from weaviate.collection.classes.types import Properties, TProperties
from weaviate.collection.query import _QueryCollection


ITERATOR_CACHE_SIZE = 100


class _ObjectIterator(Generic[Properties, TProperties], Iterable[_Object[Properties]]):
    def __init__(
        self,
        query: _QueryCollection[TProperties],
        return_metadata: Optional[MetadataQuery],
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]],
    ) -> None:
        self.__query = query

        self.__meta = return_metadata
        self.__props = return_properties

        if self.__meta is not None:
            self.__meta.uuid = True
        elif self.__props is not None:
            self.__meta = MetadataQuery(uuid=True)

        self.__iter_object_cache: List[_Object[Properties]] = []
        self.__iter_object_last_uuid: Optional[UUID] = None

    def __iter__(self) -> Iterator[_Object[Properties]]:
        self.__iter_object_cache = []
        self.__iter_object_last_uuid = None
        return self

    def __next__(self) -> _Object[Properties]:
        if len(self.__iter_object_cache) == 0:
            ret: _QueryReturn[Properties] = self.__query.fetch_objects(
                limit=ITERATOR_CACHE_SIZE,
                after=self.__iter_object_last_uuid,
                return_metadata=self.__meta,
                return_properties=self.__props,
            )
            self.__iter_object_cache = ret.objects
            if len(self.__iter_object_cache) == 0:
                raise StopIteration

        ret_object = self.__iter_object_cache.pop(0)
        self.__iter_object_last_uuid = ret_object.metadata.uuid
        assert (
            self.__iter_object_last_uuid is not None
        )  # if this is None the iterator will never stop
        return ret_object

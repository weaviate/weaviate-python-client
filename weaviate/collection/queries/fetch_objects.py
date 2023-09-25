from typing import (
    List,
    Optional,
    Union,
    Type,
)

from weaviate.collection.classes.filters import (
    _Filters,
)
from weaviate.collection.classes.grpc import (
    MetadataQuery,
    PROPERTIES,
    Sort,
)
from weaviate.collection.classes.internal import _GenerativeReturn, _Object, _Generative
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.queries.base import _Grpc
from weaviate.types import UUID


class _FetchObjectsQuery(_Grpc):
    def fetch_objects(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self._parse_return_properties(return_properties)
        res = self._query().get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self._result_to_query_return(res, ret_type)


class _FetchObjectsGenerate(_Grpc):
    def fetch_objects(
        self,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ret_properties, ret_type = self._parse_return_properties(return_properties)
        res = self._query().get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
            return_metadata=return_metadata,
            return_properties=ret_properties,
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
        )
        return self._result_to_generative_return(res, ret_type)

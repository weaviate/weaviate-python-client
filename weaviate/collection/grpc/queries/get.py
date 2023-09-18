from typing import (
    List,
    Literal,
    Optional,
    Union,
    Type,
    overload,
)

from weaviate.collection.classes.filters import (
    _Filters,
)
from weaviate.collection.classes.grpc import (
    Generate,
    MetadataQuery,
    PROPERTIES,
    Sort,
)
from weaviate.collection.classes.internal import (
    _GenerativeReturn,
    _QueryReturn,
)
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.grpc.base.wrapper import _Grpc
from weaviate.weaviate_types import UUID


class _Get(_Grpc):
    @overload
    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
        generate: Literal[None] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
        *,
        generate: Generate,
    ) -> _GenerativeReturn[Properties]:
        ...

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
        generate: Optional[Generate] = None,
    ) -> Union[_QueryReturn[Properties], _GenerativeReturn[Properties]]:
        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
            return_metadata=return_metadata,
            return_properties=ret_properties,
            generative_single=generate.single_prompt if generate is not None else None,
            generative_grouped=generate.grouped_task if generate is not None else None,
            generative_grouped_properties=generate.grouped_properties
            if generate is not None
            else None,
        )
        if generate is None:
            return self._result_to_query_return(res, ret_type)
        else:
            return self._result_to_generative_return(res, ret_type)

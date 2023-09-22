from typing import List, Literal, Optional, Type, Union, overload

from weaviate.collection.classes.filters import (
    _Filters,
)
from weaviate.collection.classes.grpc import (
    GroupBy,
    MetadataQuery,
    PROPERTIES,
)
from weaviate.collection.classes.internal import (
    _Generative,
    _GenerativeReturn,
    _GroupBy,
    _GroupByReturn,
    _QueryReturn,
)
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.queries.base import _Grpc
from weaviate.types import UUID


class _NearObjectQuery(_Grpc):
    @overload
    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        *,
        group_by: GroupBy,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GroupByReturn[Properties]:
        ...

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> Union[_GroupByReturn[Properties], _QueryReturn[Properties]]:
        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().near_object(
            near_object=near_object,
            certainty=certainty,
            distance=distance,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        if group_by is None:
            return self._result_to_query_return(res, ret_type)
        else:
            return self._result_to_groupby_return(res, ret_type)


class _NearObjectGenerate(_Grpc):
    def near_object(
        self,
        near_object: UUID,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().near_object(
            near_object=near_object,
            certainty=certainty,
            distance=distance,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self._result_to_generative_return(res, ret_type)

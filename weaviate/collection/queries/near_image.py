from typing import Literal, Optional, Type, Union, overload

from weaviate.collection.classes.filters import (
    _Filters,
)
from weaviate.collection.classes.grpc import MetadataQuery, PROPERTIES, Generate, GroupBy
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


class _NearImage(_Grpc):
    @overload
    def near_image(
        self,
        near_image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        generate: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def near_image(
        self,
        near_image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        *,
        generate: Generate,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ...

    @overload
    def near_image(
        self,
        near_image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        *,
        group_by: GroupBy,
        generate: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GroupByReturn[Properties]:
        ...

    def near_image(
        self,
        near_image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        generate: Optional[Generate] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> Union[_GenerativeReturn[Properties], _GroupByReturn[Properties], _QueryReturn[Properties]]:
        if generate is not None and group_by is not None:
            raise ValueError("Cannot have group_by and generate defined simultaneously")

        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().near_image(
            image=near_image,
            certainty=certainty,
            distance=distance,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            generative=_Generative.from_input(generate),
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        if generate is None and group_by is None:
            return self._result_to_query_return(res, ret_type)
        elif generate is not None:
            return self._result_to_generative_return(res, ret_type)
        else:
            return self._result_to_groupby_return(res, ret_type)

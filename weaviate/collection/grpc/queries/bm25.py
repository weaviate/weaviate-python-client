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
)
from weaviate.collection.classes.internal import (
    _GenerativeReturn,
    _QueryReturn,
)
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.grpc.base.wrapper import _Grpc


class _BM25(_Grpc):
    @overload
    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        generate: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        *,
        generate: Generate,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ...

    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        generate: Optional[Generate] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> Union[_QueryReturn[Properties], _GenerativeReturn[Properties]]:
        ret_properties, ret_type = self._determine_generic(return_properties)
        res = self._query().bm25(
            query=query,
            properties=query_properties,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
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

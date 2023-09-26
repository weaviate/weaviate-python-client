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
)
from weaviate.collection.classes.internal import _GenerativeReturn, _QueryReturn, _Generative
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.collection.queries.base import _Grpc


class _BM25Query(_Grpc):
    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        """Search for objects in this collection using the keyword-based BM25 algorithm.

        See the [docs](https://weaviate.io/developers/weaviate/search/bm25) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `return_metadata`
                The metadata to return for each object.
            `return_properties`
                The properties to return for each object.

        NOTE:
            If neither `return_metadata` nor `return_properties` are provided then all properties and metadata are returned except for `metadata.vector`.

        Returns:
            A `_QueryReturn` object that includes the searched objects.

        Raises:
            `weaviate.exceptions.WeaviateGRPCException`:
                If the network connection to Weaviate fails.
        """
        ret_properties, ret_type = self._parse_return_properties(return_properties)
        res = self._query().bm25(
            query=query,
            properties=query_properties,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self._result_to_query_return(res, ret_type)


class _BM25Generate(_Grpc):
    def bm25(
        self,
        query: str,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        """Search for objects in this collection using the keyword-based BM25 algorithm and perform retrieval-augmented generation (RaG) on the results.

        See the [docs](https://weaviate.io/developers/weaviate/search/bm25) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED.
            `single_prompt`
                The prompt to use for RaG on each object individually.
            `grouped_task`
                The prompt to use for RaG on the entire result set.
            `grouped_properties`
                The properties to use in the RaG on the entire result set.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `return_metadata`
                The metadata to return for each object.
            `return_properties`
                The properties to return for each object.

        NOTE:
            If neither `return_metadata` nor `return_properties` are provided then all properties and metadata are returned except for `metadata.vector`.

        Returns:
            A `_GenerativeReturn` object that includes the searched objects including per-object generated results and grouped generated results.

        Raises:
            `weaviate.exceptions.WeaviateGRPCException`:
                If the network connection to Weaviate fails.
        """
        ret_properties, ret_type = self._parse_return_properties(return_properties)
        res = self._query().bm25(
            query=query,
            properties=query_properties,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
            return_metadata=return_metadata,
            return_properties=ret_properties,
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
        )
        return self._result_to_generative_return(res, ret_type)

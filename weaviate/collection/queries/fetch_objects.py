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
from weaviate.collection.classes.internal import _GenerativeReturn, _QueryReturn, _Generative
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
    ) -> _QueryReturn[Properties]:
        """Retrieve the objects in this collection without any search.

        Arguments:
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `offset`
                The offset to start from. If not specified, the retrieval begins from the first object in the server.
            `after`
                The UUID of the object to start from. If not specified, the retrieval begins from the first object in the server.
            `filters`
                The filters to apply to the retrieval.
            `sort`
                The sorting to apply to the retrieval.
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
        """Retrieve the objects in this collection without any search and perform retrieval-augmented generation (RaG) on the results.

        Arguments:
            `single_prompt`
                The prompt to use for RaG on each object individually.
            `grouped_task`
                The prompt to use for RaG on the entire result set.
            `grouped_properties`
                The properties to use in the RaG on the entire result set.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by Weaviate is returned.
            `offset`
                The offset to start from. If not specified, the retrieval begins from the first object in Weaviate.
            `after`
                The UUID of the object to start from. If not specified, the retrieval begins from the first object in Weaviate.
            `filters`
                The filters to apply to the retrieval.
            `sort`
                The sorting to apply to the retrieval.
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

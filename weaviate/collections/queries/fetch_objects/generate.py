from typing import Generic, List, Optional

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, _Sorting
from weaviate.collections.classes.internal import (
    GenerativeReturnType,
    _Generative,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseQuery
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsGenerate(Generic[Properties, References], _BaseQuery[Properties, References]):
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> GenerativeReturnType[Properties, References, TProperties, TReferences]:
        """Perform retrieval-augmented generation (RaG) on the results of a simple get query of objects in this collection.

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
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `_GenerativeNearMediaReturn` object that includes the searched objects with per-object generated results and group generated results.

        Raises:
            `weaviate.exceptions.WeaviateGRPCQueryError`:
                If the network connection to Weaviate fails.
        """
        res = self._query.get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
        )
        return self._result_to_generative_query_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
            ),
            return_properties,
            return_references,
        )

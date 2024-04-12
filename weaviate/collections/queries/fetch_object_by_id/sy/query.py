from typing import (
    Generic,
    Optional,
)
from weaviate.collections.classes.internal import (
    QuerySingleReturn,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base_sync import _BaseQuery
from weaviate.types import INCLUDE_VECTOR, UUID


class _FetchObjectByIDQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> QuerySingleReturn[Properties, References, TProperties, TReferences]:
        """Retrieve an object from the server by its UUID.

        Arguments:
            `uuid`
                The UUID of the object to retrieve, REQUIRED.
            `include_vector`
                Whether to include the vector in the returned object.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

        Raises:
            `weaviate.exceptions.WeaviateGRPCQueryError`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        return self._loop.run_until_complete(
            self._query.fetch_object_by_id,
            uuid,
            include_vector=include_vector,
            return_properties=return_properties,
            return_references=return_references,
        )

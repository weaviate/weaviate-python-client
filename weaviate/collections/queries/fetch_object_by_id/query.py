from typing import (
    Generic,
    Optional,
    cast,
)

from weaviate import syncify
from weaviate.collections.classes.filters import (
    Filter,
)
from weaviate.collections.classes.grpc import MetadataQuery
from weaviate.collections.classes.internal import (
    ObjectSingleReturn,
    MetadataSingleObjectReturn,
    QuerySingleReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _Base
from weaviate.types import INCLUDE_VECTOR, UUID


class _FetchObjectByIDQueryAsync(Generic[Properties, References], _Base[Properties, References]):
    async def fetch_object_by_id(
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
        return_metadata = MetadataQuery(
            creation_time=True, last_update_time=True, is_consistent=True
        )
        res = await self._query.get(
            limit=1,
            filters=Filter.by_id().equal(uuid),
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        objects = self._result_to_query_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
            ),
            return_properties,
            None,
        )

        if len(objects.objects) == 0:
            return None

        obj = objects.objects[0]
        assert obj.metadata is not None
        assert obj.metadata.creation_time is not None
        assert obj.metadata.last_update_time is not None

        return cast(
            QuerySingleReturn[Properties, References, TProperties, TReferences],
            ObjectSingleReturn(
                uuid=obj.uuid,
                vector=obj.vector,
                properties=obj.properties,
                metadata=MetadataSingleObjectReturn(
                    creation_time=obj.metadata.creation_time,
                    last_update_time=obj.metadata.last_update_time,
                    is_consistent=obj.metadata.is_consistent,
                ),
                references=obj.references,
                collection=obj.collection,
            ),
        )


@syncify.convert
class _FetchObjectByIDQuery(
    Generic[Properties, References], _FetchObjectByIDQueryAsync[Properties, References]
):
    pass

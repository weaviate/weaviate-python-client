from typing import Generic, Optional

from weaviate.collections.classes.filters import (
    FilterMetadata,
)
from weaviate.collections.classes.grpc import MetadataQuery

from weaviate.collections.classes.internal import (
    _Object,
    ReturnProperties,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties
from weaviate.collections.queries.base import _Grpc
from weaviate.types import UUID


class _FetchObjectByIDQuery(Generic[Properties], _Grpc[Properties]):
    def fetch_object_by_id(
        self,
        uuid: UUID,
        return_properties: Optional[ReturnProperties[Properties]] = None,
        include_vector: bool = False,
    ) -> Optional[_Object[Properties]]:
        """Retrieve an object from the server by its UUID.

        Arguments:
            `uuid`
                The UUID of the object to retrieve, REQUIRED.
            `return_properties`
                The properties to return for each object.
            `include_vector`
                Whether to include the vector in the returned object.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        return_metadata = MetadataQuery(
            creation_time_unix=True, last_update_time_unix=True, is_consistent=True
        )
        res = self._query().get(
            limit=1,
            filters=FilterMetadata.ById.equal(uuid),
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
        )
        objects = self._result_to_query_return(
            res,
            return_properties,
            _QueryOptions.from_input(return_metadata, return_properties, include_vector),
        )

        if len(objects.objects) == 0:
            return None

        return objects.objects[0]

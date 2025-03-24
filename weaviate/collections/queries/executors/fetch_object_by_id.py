from typing import (
    Generic,
    Optional,
    cast,
)

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
from weaviate.collections.queries.executors.base import _BaseExecutor
from weaviate.connect.v4 import Connection
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import INCLUDE_VECTOR, UUID


class _FetchObjectsByIdQueryExecutor(Generic[Properties, References], _BaseExecutor):
    def fetch_object_by_id(
        self,
        *,
        connection: Connection,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]],
    ) -> ExecutorResult[QuerySingleReturn[Properties, References, TProperties, TReferences]]:
        return_metadata = MetadataQuery(
            creation_time=True, last_update_time=True, is_consistent=True
        )

        def resp(
            res: SearchReply,
        ) -> QuerySingleReturn[Properties, References, TProperties, TReferences]:
            objects = self._result_to_query_return(
                res,
                _QueryOptions.from_input(
                    return_metadata,
                    return_properties,
                    include_vector,
                    self._references,
                    return_references,
                ),
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

        request = self._query.get(
            limit=1,
            filters=Filter.by_id().equal(uuid),
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return execute(response_callback=resp, method=connection.grpc_search, request=request)

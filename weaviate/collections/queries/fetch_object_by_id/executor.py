from typing import Generic, Literal, Optional, Type, Union, cast, overload

from weaviate.collections.classes.filters import (
    Filter,
)
from weaviate.collections.classes.grpc import MetadataQuery, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    ObjectSingleReturn,
    CrossReferences,
    MetadataSingleObjectReturn,
    QuerySingleReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import INCLUDE_VECTOR, UUID


class _FetchObjectByIDQueryExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> executor.Result[ObjectSingleReturn[Properties, References]]: ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> executor.Result[ObjectSingleReturn[Properties, CrossReferences]]: ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences],
    ) -> executor.Result[ObjectSingleReturn[Properties, TReferences]]: ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> executor.Result[ObjectSingleReturn[TProperties, References]]: ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> executor.Result[ObjectSingleReturn[TProperties, CrossReferences]]: ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> executor.Result[ObjectSingleReturn[TProperties, TReferences]]: ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[QuerySingleReturn[Properties, References, TProperties, TReferences]]: ...

    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ):
        """Retrieve an object from the server by its UUID.

        Args:
            uuid: The UUID of the object to retrieve, REQUIRED.
            include_vector: Whether to include the vector in the returned object.
            return_properties: The properties to return for each object.
            return_references: The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

        Raises:
            weaviate.exceptions.WeaviateGRPCQueryError: If the network connection to Weaviate fails.
            weaviate.exceptions.WeaviateInsertInvalidPropertyError: If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
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
        return executor.execute(
            response_callback=resp, method=self._connection.grpc_search, request=request
        )

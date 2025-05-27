from typing import (
    Any,
    Generic,
    Iterable,
    Literal,
    Optional,
    Type,
    Union,
    cast,
    overload,
)

from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, Sorting
from weaviate.collections.classes.internal import (
    CrossReferences,
    QueryReturn,
    QueryReturnType,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import (
    Properties,
    References,
    TProperties,
    TReferences,
)
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync, ConnectionType
from weaviate.proto.v1 import search_get_pb2
from weaviate.types import INCLUDE_VECTOR, UUID


class _FetchObjectsByIDsQueryExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> executor.Result[QueryReturn[Properties, References]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> executor.Result[QueryReturn[Properties, CrossReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences],
    ) -> executor.Result[QueryReturn[Properties, TReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> executor.Result[QueryReturn[TProperties, References]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> executor.Result[QueryReturn[TProperties, CrossReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> executor.Result[QueryReturn[TProperties, TReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[QueryReturnType[Properties, References, TProperties, TReferences]]: ...

    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[QueryReturnType[Properties, References, TProperties, TReferences]]:
        """Perform a special case of fetch_objects based on filters on uuid.

        See the docstring of `fetch_objects` for more information on the arguments.
        """

        def resp(
            res: search_get_pb2.SearchReply,
        ) -> QueryReturnType[Properties, References, TProperties, TReferences]:
            return cast(
                Any,
                self._result_to_query_return(
                    res,
                    _QueryOptions.from_input(
                        return_metadata,
                        return_properties,
                        include_vector,
                        self._references,
                        return_references,
                    ),
                ),
            )

        if not ids:
            if isinstance(self._connection, ConnectionAsync):

                async def _execute() -> QueryReturnType[
                    Properties, References, TProperties, TReferences
                ]:
                    return resp(search_get_pb2.SearchReply())

                return _execute()
            return resp(search_get_pb2.SearchReply())

        request = self._query.get(
            limit=limit,
            offset=offset,
            after=after,
            filters=Filter.any_of([Filter.by_id().equal(uuid) for uuid in ids]),
            sort=sort,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(cast(Any, return_references)),
        )
        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_search,
            request=request,
        )

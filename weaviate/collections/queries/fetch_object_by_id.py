from typing import Generic, Literal, Optional, Union, Type, cast, overload

from weaviate.collections.classes.filters import (
    FilterMetadata,
)
from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES, MetadataQuery

from weaviate.collections.classes.internal import (
    _MetadataSingleObjectReturn,
    _ObjectSingleReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    References,
    WeaviateReferences,
    TReferences,
)
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.queries.base import _BaseQuery
from weaviate.types import UUID


class _FetchObjectByIDQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _ObjectSingleReturn[Properties, References]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _ObjectSingleReturn[Properties, WeaviateReferences]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _ObjectSingleReturn[Properties, TReferences]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _ObjectSingleReturn[TProperties, References]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _ObjectSingleReturn[TProperties, WeaviateReferences]:
        ...

    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _ObjectSingleReturn[TProperties, TReferences]:
        ...

    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: bool = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> Union[
        None,
        _ObjectSingleReturn[Properties, References],
        _ObjectSingleReturn[Properties, WeaviateReferences],
        _ObjectSingleReturn[Properties, TReferences],
        _ObjectSingleReturn[TProperties, References],
        _ObjectSingleReturn[TProperties, WeaviateReferences],
        _ObjectSingleReturn[TProperties, TReferences],
    ]:
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
        assert obj.metadata.creation_time_unix is not None
        assert obj.metadata.last_update_time_unix is not None

        return cast(
            Union[
                None,
                _ObjectSingleReturn[Properties, References],
                _ObjectSingleReturn[Properties, WeaviateReferences],
                _ObjectSingleReturn[Properties, TReferences],
                _ObjectSingleReturn[TProperties, References],
                _ObjectSingleReturn[TProperties, WeaviateReferences],
                _ObjectSingleReturn[TProperties, TReferences],
            ],
            _ObjectSingleReturn(
                uuid=obj.uuid,
                vector=obj.vector,
                properties=obj.properties,
                metadata=_MetadataSingleObjectReturn(
                    creation_time_unix=obj.metadata.creation_time_unix,
                    last_update_time_unix=obj.metadata.last_update_time_unix,
                    is_consistent=obj.metadata.is_consistent,
                ),
                references=obj.references,
            ),
        )

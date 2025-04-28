from typing import Generic, Literal, Optional, Type, Union, overload

from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    CrossReferences,
    ObjectSingleReturn,
    QuerySingleReturn,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, References, TProperties, TReferences
from weaviate.connect.v4 import ConnectionSync
from weaviate.types import INCLUDE_VECTOR, UUID

from .executor import _FetchObjectByIDQueryExecutor

class _FetchObjectByIDQuery(
    Generic[Properties, References],
    _FetchObjectByIDQueryExecutor[ConnectionSync, Properties, References],
):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[Properties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[Properties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences],
    ) -> ObjectSingleReturn[Properties, TReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[TProperties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[TProperties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> ObjectSingleReturn[TProperties, TReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> QuerySingleReturn[Properties, References, TProperties, TReferences]: ...

from typing import Generic, Literal, Optional, Type, Union, overload
from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    ObjectSingleReturn,
    CrossReferences,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
    References,
    TReferences,
    Vectors,
)
from weaviate.collections.queries.base import _BaseQuery
from weaviate.types import UUID

class _FetchObjectByIDQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> ObjectSingleReturn[Properties, None, None]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> ObjectSingleReturn[Properties, CrossReferences, None]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> ObjectSingleReturn[Properties, TReferences, None]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> ObjectSingleReturn[TProperties, None, None]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> ObjectSingleReturn[TProperties, CrossReferences, None]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> ObjectSingleReturn[TProperties, TReferences, None]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> ObjectSingleReturn[Properties, None, Vectors]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> ObjectSingleReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> ObjectSingleReturn[Properties, TReferences, Vectors]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> ObjectSingleReturn[TProperties, None, Vectors]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> ObjectSingleReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> ObjectSingleReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> Union[
        ObjectSingleReturn[Properties, None, None], ObjectSingleReturn[Properties, None, Vectors]
    ]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> Union[
        ObjectSingleReturn[Properties, CrossReferences, None],
        ObjectSingleReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> Union[
        ObjectSingleReturn[Properties, TReferences, None],
        ObjectSingleReturn[Properties, TReferences, Vectors],
    ]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> Union[
        ObjectSingleReturn[TProperties, None, None], ObjectSingleReturn[TProperties, None, Vectors]
    ]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> Union[
        ObjectSingleReturn[TProperties, CrossReferences, None],
        ObjectSingleReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        *,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> Union[
        ObjectSingleReturn[TProperties, TReferences, None],
        ObjectSingleReturn[TProperties, TReferences, Vectors],
    ]: ...

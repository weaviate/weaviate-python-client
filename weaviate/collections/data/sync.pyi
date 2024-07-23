import uuid as uuid_package
from typing import (
    Optional,
    List,
    Literal,
    Sequence,
    Generic,
    Type,
    Union,
    overload,
)

from weaviate.collections.classes.batch import (
    DeleteManyObject,
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyReturn,
)
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
    TProperties,
)
from weaviate.collections.classes.types import (
    Properties,
)
from weaviate.collections.data.data import _DataBase
from weaviate.types import UUID, VECTORS

class _DataCollection(Generic[Properties], _DataBase):
    def with_data_model(self, data_model: Type[TProperties]) -> "_DataCollection[TProperties]": ...
    def insert(
        self,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> uuid_package.UUID: ...
    def insert_many(
        self,
        objects: Sequence[Union[Properties, DataObject[Properties, Optional[ReferenceInputs]]]],
    ) -> BatchObjectReturn: ...
    def replace(
        self,
        uuid: UUID,
        properties: Properties,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[VECTORS] = None,
    ) -> None: ...
    def update(
        self,
        uuid: UUID,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        vector: Optional[VECTORS] = None,
    ) -> None: ...
    def reference_add(
        self, from_uuid: UUID, from_property: str, to: SingleReferenceInput
    ) -> None: ...
    def reference_add_many(self, refs: List[DataReferences]) -> BatchReferenceReturn: ...
    def reference_delete(
        self, from_uuid: UUID, from_property: str, to: SingleReferenceInput
    ) -> None: ...
    def reference_replace(
        self, from_uuid: UUID, from_property: str, to: ReferenceInput
    ) -> None: ...
    def exists(self, uuid: UUID) -> bool: ...
    def delete_by_id(self, uuid: UUID) -> bool: ...
    @overload
    def delete_many(
        self, where: _Filters, verbose: Literal[False] = ..., *, dry_run: bool = False
    ) -> DeleteManyReturn[None]: ...
    @overload
    def delete_many(
        self, where: _Filters, verbose: Literal[True], *, dry_run: bool = False
    ) -> DeleteManyReturn[List[DeleteManyObject]]: ...
    @overload
    def delete_many(
        self, where: _Filters, verbose: bool = ..., *, dry_run: bool = False
    ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]: ...

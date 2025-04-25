import uuid as uuid_package
from typing import Generic, List, Literal, Optional, Sequence, Union, overload

from weaviate.collections.classes.batch import (
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyObject,
    DeleteManyReturn,
)
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    ReferenceInput,
    ReferenceInputs,
    SingleReferenceInput,
)
from weaviate.collections.classes.types import Properties
from weaviate.connect.v4 import ConnectionSync
from weaviate.types import UUID, VECTORS

from .executor import _DataCollectionExecutor

class _DataCollection(Generic[Properties,], _DataCollectionExecutor[ConnectionSync, Properties]):
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
    def exists(self, uuid: UUID) -> bool: ...
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
    def delete_by_id(self, uuid: UUID) -> bool: ...
    @overload
    def delete_many(
        self, where: _Filters, *, verbose: Literal[False] = False, dry_run: bool = False
    ) -> DeleteManyReturn[None]: ...
    @overload
    def delete_many(
        self, where: _Filters, *, verbose: Literal[True], dry_run: bool = False
    ) -> DeleteManyReturn[List[DeleteManyObject]]: ...
    @overload
    def delete_many(
        self, where: _Filters, *, verbose: bool = False, dry_run: bool = False
    ) -> Union[DeleteManyReturn[List[DeleteManyObject]], DeleteManyReturn[None]]: ...

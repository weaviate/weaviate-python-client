import asyncio
import datetime
import uuid as uuid_package
from typing import (
    Any,
    Dict,
    Generic,
    Optional,
    List,
    Literal,
    Mapping,
    Sequence,
    Tuple,
    Type,
    Union,
    cast,
    overload,
)
from httpx import Response
from weaviate.collections.classes.batch import (
    DeleteManyObject,
    _BatchObject,
    _BatchReference,
    BatchObjectReturn,
    BatchReferenceReturn,
    DeleteManyReturn,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.data import DataObject, DataReferences
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.internal import (
    _Reference,
    ReferenceToMulti,
    SingleReferenceInput,
    ReferenceInput,
    ReferenceInputs,
)
from weaviate.collections.classes.types import (
    GeoCoordinate,
    PhoneNumber,
    _PhoneNumber,
    Properties,
    WeaviateField,
)
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, ConnectionType
from weaviate.logger import logger
from weaviate.types import BEACON, UUID, VECTORS
from weaviate.util import _datetime_to_string, _get_vector_v4
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.collections.batch.grpc_batch_objects import _BatchGRPC
from weaviate.collections.batch.grpc_batch_delete import _BatchDeleteGRPC
from weaviate.collections.batch.rest import _BatchREST
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.connect.v4 import ConnectionSync
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

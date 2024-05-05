import uuid as uuid_package
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, cast

from pydantic import BaseModel, Field, field_validator

from weaviate.collections.classes.internal import ReferenceInputs
from weaviate.collections.classes.types import WeaviateField
from weaviate.types import BEACON, UUID, VECTORS
from weaviate.util import _capitalize_first_letter, get_valid_uuid, _get_vector_v4


@dataclass
class _BatchObject:
    collection: str
    vector: Optional[VECTORS]
    uuid: str
    properties: Optional[Dict[str, WeaviateField]]
    tenant: Optional[str]
    references: Optional[ReferenceInputs]
    retry_count: int = 0


@dataclass
class _BatchReference:
    from_: str
    to: str
    tenant: Optional[str]
    from_uuid: str


class BatchObject(BaseModel):
    """
    A Weaviate object to be added to the database.

    Performs validation on the class name and UUID, and automatically generates a UUID if one is not provided.
    Also converts the vector to a list of floats if it is provided as a numpy array.
    """

    collection: str = Field(min_length=1)
    properties: Optional[Dict[str, Any]] = Field(default=None)
    references: Optional[ReferenceInputs] = Field(default=None)
    uuid: Optional[UUID] = Field(default=None)
    vector: Optional[VECTORS] = Field(default=None)
    tenant: Optional[str] = Field(default=None)

    def __init__(self, **data: Any) -> None:
        v = data.get("vector")
        if v is not None:
            if isinstance(v, dict):  # named vector
                for key, val in v.items():
                    v[key] = _get_vector_v4(val)
                data["vector"] = v
            else:
                data["vector"] = _get_vector_v4(v)

        data["uuid"] = (
            get_valid_uuid(u) if (u := data.get("uuid")) is not None else uuid_package.uuid4()
        )
        super().__init__(**data)

    def _to_internal(self) -> _BatchObject:
        return _BatchObject(
            collection=self.collection,
            vector=cast(list, self.vector),
            uuid=str(self.uuid),
            properties=self.properties,
            tenant=self.tenant,
            references=self.references,
        )

    @field_validator("collection")
    def _validate_collection(cls, v: str) -> str:
        return _capitalize_first_letter(v)


class Shard(BaseModel):
    """Use this class when defining a shard whose vector indexing process will be awaited for in a sync blocking fashion."""

    collection: str
    tenant: Optional[str] = Field(default=None)

    def __hash__(self) -> int:
        return hash((self.collection, self.tenant))


class BatchReference(BaseModel):
    """
    A reference between two objects in Weaviate.

    Performs validation on the class names and UUIDs.

    Converts provided data to an internal object containing beacons for insertion into Weaviate.
    """

    from_object_collection: str = Field(min_length=1)
    from_object_uuid: UUID
    from_property_name: str
    to_object_uuid: UUID
    to_object_collection: Optional[str] = None
    tenant: Optional[str] = None

    @field_validator("from_object_collection")
    def _validate_from_object_collection(cls, v: str) -> str:
        return _capitalize_first_letter(v)

    @field_validator("to_object_collection")
    def _validate_to_object_collection(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v is not None and len(v) == 0:
            raise ValueError("to_object_collection must not be empty if provided")
        return _capitalize_first_letter(v)

    @field_validator("to_object_uuid", "from_object_uuid")
    def _validate_uuids(cls, v: UUID) -> str:
        return get_valid_uuid(v)

    def _to_internal(self) -> _BatchReference:
        if self.to_object_collection is None:
            self.to_object_collection = ""
        else:
            self.to_object_collection = self.to_object_collection + "/"
        return _BatchReference(
            from_uuid=str(self.from_object_uuid),
            from_=f"{BEACON}{self.from_object_collection}/{self.from_object_uuid}/{self.from_property_name}",
            to=f"{BEACON}{self.to_object_collection}{str(self.to_object_uuid)}",
            tenant=self.tenant,
        )


@dataclass
class ErrorObject:
    """This class contains the error information for a single object in a batch operation."""

    message: str
    object_: _BatchObject
    original_uuid: Optional[UUID] = None


@dataclass
class ErrorReference:
    """This class contains the error information for a single reference in a batch operation."""

    message: str
    reference: _BatchReference


@dataclass
class BatchObjectReturn:
    """This class contains the results of a batch `insert_many` operation.

    Since the individual objects within the batch can error for differing reasons, the data is split up within this class for ease use when performing error checking, handling, and data revalidation.

    Attributes:
        `all_responses`
            A list of all the responses from the batch operation. Each response is either a `uuid_package.UUID` object or an `Error` object.
        `elapsed_seconds`
            The time taken to perform the batch operation.
        `errors`
            A dictionary of all the failed responses from the batch operation. The keys are the indices of the objects in the batch, and the values are the `Error` objects.
        `uuids`
            A dictionary of all the successful responses from the batch operation. The keys are the indices of the objects in the batch, and the values are the `uuid_package.UUID` objects.
        `has_errors`
            A boolean indicating whether or not any of the objects in the batch failed to be inserted. If this is `True`, then the `errors` dictionary will contain at least one entry.
    """

    all_responses: List[Union[uuid_package.UUID, ErrorObject]]
    elapsed_seconds: float
    errors: Dict[int, ErrorObject]
    uuids: Dict[int, uuid_package.UUID]
    has_errors: bool = False

    def __add__(self, other: "BatchObjectReturn") -> "BatchObjectReturn":
        self.all_responses += other.all_responses

        prev_max = max(self.errors.keys()) if len(self.errors) > 0 else -1
        for k1, v1 in other.errors.items():
            self.errors[prev_max + k1] = v1

        prev_max = max(self.uuids.keys()) if len(self.uuids) > 0 else -1
        for k1, v2 in other.uuids.items():
            self.uuids[prev_max + k1] = v2

        self.has_errors = self.has_errors or other.has_errors
        return self


@dataclass
class BatchReferenceReturn:
    """This class contains the results of a batch `insert_many_references` operation.

    Since the individual references within the batch can error for differing reasons, the data is split up within this class for ease use when performing error checking, handling, and data revalidation.

    Attributes:
        `elapsed_seconds`
            The time taken to perform the batch operation.
        `errors`
            A dictionary of all the failed responses from the batch operation. The keys are the indices of the references in the batch, and the values are the `Error` objects.
        `has_errors`
            A boolean indicating whether or not any of the references in the batch failed to be inserted. If this is `True`, then the `errors` dictionary will contain at least one entry.
    """

    elapsed_seconds: float
    errors: Dict[int, ErrorReference]
    has_errors: bool = False

    def __add__(self, other: "BatchReferenceReturn") -> "BatchReferenceReturn":
        self.elapsed_seconds += other.elapsed_seconds
        prev_max = max(self.errors.keys()) if len(self.errors) > 0 else -1
        for key, value in other.errors.items():
            self.errors[prev_max + key] = value
        self.has_errors = self.has_errors or other.has_errors
        return self


class BatchResult:
    """This class contains the results of a batch operation.

    Since the individual objects and references within the batch can error for differing reasons, the data is split up
    within this class for ease use when performing error checking, handling, and data revalidation.

    Attributes:
        `objs`
            The results of the batch object operation.
        `refs`
            The results of the batch reference operation.
    """

    def __init__(self) -> None:
        self.objs: BatchObjectReturn = BatchObjectReturn([], 0.0, {}, {})
        self.refs: BatchReferenceReturn = BatchReferenceReturn(0.0, {})


@dataclass
class DeleteManyObject:
    """This class contains the objects of a `delete_many` operation."""

    uuid: uuid_package.UUID
    successful: bool
    error: Optional[str] = None


# generic type for DeleteManyReturn
T = TypeVar("T")


@dataclass
class DeleteManyReturn(Generic[T]):
    """This class contains the results of a `delete_many` operation.."""

    failed: int
    matches: int
    objects: T
    successful: int


class BatchRetryConfig(BaseModel):
    """Configuration for retrying failed batch operations."""

    max_retries: int = 3
    retry_on_error_message_contains: List[str] = Field(default_factory=list)
    retry_wait_time: int = 0

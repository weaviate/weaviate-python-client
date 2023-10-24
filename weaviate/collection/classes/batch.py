import uuid as uuid_package
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union, cast

from pydantic import BaseModel, Field, field_validator

from weaviate.util import _capitalize_first_letter, get_valid_uuid, get_vector
from weaviate.weaviate_types import BEACON, UUID, WeaviateField


@dataclass
class _BatchObject:
    class_name: str
    vector: Optional[List[float]]
    uuid: Optional[UUID]
    properties: Dict[str, WeaviateField]
    tenant: Optional[str]


@dataclass
class _BatchReference:
    from_: str
    to: str
    tenant: Optional[str]


class BatchObject(BaseModel):
    """
    A Weaviate object to be added to the database.

    Performs validation on the class name and UUID, and automatically generates a UUID if one is not provided.
    Also converts the vector to a list of floats if it is provided as a numpy array.
    """

    class_name: str
    properties: Dict[str, Any]
    uuid: Optional[UUID] = Field(default=None)
    vector: Optional[Sequence] = Field(default=None)
    tenant: Optional[str] = Field(default=None)

    def __init__(self, **data: Any) -> None:
        data["vector"] = get_vector(v) if (v := data.get("vector")) is not None else None
        data["uuid"] = (
            get_valid_uuid(u) if (u := data.get("uuid")) is not None else uuid_package.uuid4()
        )
        super().__init__(**data)

    def _to_internal(self) -> _BatchObject:
        return _BatchObject(
            class_name=self.class_name,
            vector=cast(list, self.vector),
            uuid=self.uuid,
            properties=self.properties,
            tenant=self.tenant,
        )

    @field_validator("class_name")
    def _validate_class_name(cls, v: str) -> str:
        if len(v) == 0:
            raise ValueError("class_name must not be empty")
        return _capitalize_first_letter(v)


class BatchReference(BaseModel):
    """
    A reference between two objects in Weaviate.

    Performs validation on the class names and UUIDs.

    Converts provided data to an internal object containing beacons for insertion into Weaviate.
    """

    from_object_class_name: str
    from_object_uuid: UUID
    from_property_name: str
    to_object_uuid: UUID
    to_object_class_name: Optional[str] = None
    tenant: Optional[str] = None

    @field_validator("from_object_class_name")
    def _validate_from_object_class_name(cls, v: str) -> str:
        if len(v) == 0:
            raise ValueError("from_object_class_name must not be empty")
        return _capitalize_first_letter(v)

    @field_validator("to_object_class_name")
    def _validate_to_object_class_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v is not None and len(v) == 0:
            raise ValueError("to_object_class_name must not be empty if provided")
        return _capitalize_first_letter(v)

    @field_validator("to_object_uuid", "from_object_uuid")
    def _validate_uuids(cls, v: UUID) -> str:
        return get_valid_uuid(v)

    def _to_internal(self) -> _BatchReference:
        if self.to_object_class_name is None:
            self.to_object_class_name = ""
        else:
            self.to_object_class_name = self.to_object_class_name + "/"
        return _BatchReference(
            from_=f"{BEACON}{self.from_object_class_name}/{self.from_object_uuid}/{self.from_property_name}",
            to=f"{BEACON}{self.to_object_class_name}{str(self.to_object_uuid)}",
            tenant=self.tenant,
        )


@dataclass
class BatchObjectRequestBody:
    fields: List[str]
    objects: List[_BatchObject]


@dataclass
class ErrorObject:
    message: str
    object_: _BatchObject
    code: Optional[int] = None
    original_uuid: Optional[UUID] = None


@dataclass
class ErrorReference:
    message: str
    reference: _BatchReference
    code: Optional[int] = None


@dataclass
class BatchObjectReturn:
    """This class contains the results of a batch `insert_many` operation.

    Since the individual objects within the batch can error for differing reasons, the data is split up within this class for ease use when performing error checking, handling, and data revalidation.

    Attributes:
        `all_responses`
            A list of all the responses from the batch operation. Each response is either a `uuid_package.UUID` object or an `Error` object.
        `uuids`
            A dictionary of all the successful responses from the batch operation. The keys are the indices of the objects in the batch, and the values are the `uuid_package.UUID` objects.
        `errors`
            A dictionary of all the failed responses from the batch operation. The keys are the indices of the objects in the batch, and the values are the `Error` objects.
        `elapsed_seconds`
            The time taken to perform the batch operation.
        `has_errors`
            A boolean indicating whether or not any of the objects in the batch failed to be inserted. If this is `True`, then the `errors` dictionary will contain at least one entry.
    """

    all_responses: List[Union[uuid_package.UUID, ErrorObject]]
    uuids: Dict[int, uuid_package.UUID]
    errors: Dict[int, ErrorObject]
    elapsed_seconds: float
    has_errors: bool = False


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

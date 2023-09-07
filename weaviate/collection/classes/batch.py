import uuid as uuid_package
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union

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

    Attributes
    ---
    class_name : str
        The name of the class this object belongs to.
    data_object : dict
        Object to be added as a dict datatype.
    uuid : str or None, optional
        UUID of the object as a string, by default None
    vector: Sequence or None, optional
        The embedding of the object that should be validated.
        Can be used when:
        - a class does not have a vectorization module.
        - The given vector was generated using the _identical_ vectorization module that is configured for the
            class. In this case this vector takes precedence.
        Supported types are `list`, `numpy.ndarray`, `torch.Tensor` and `tf.Tensor`,
        by default None.
    tenant: str, optional
        Tenant of the object
    """

    data_object: Dict[str, Any]
    class_name: str
    uuid: UUID = Field(default_factory=lambda: uuid_package.uuid4())
    vector: Optional[Sequence] = Field(default=None)
    tenant: Optional[str] = Field(default=None)

    def _to_internal(self) -> _BatchObject:
        return _BatchObject(
            class_name=self.class_name,
            vector=get_vector(self.vector) if self.vector is not None else None,
            uuid=get_valid_uuid(self.uuid),
            properties=self.data_object,
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

    Attributes
    ---
    from_object_class_name : str
        The name of the class that should reference another object.
    from_object_uuid : str
        The UUID or URL of the object that should reference another object.
    from_property_name : str
        The name of the property that contains the reference.
    to_object_uuid : str
        The UUID or URL of the object that is actually referenced.
    to_object_class_name : Optional[str], optional
        The referenced object class name to which to add the reference (with UUID
        `to_object_uuid`), it is included in Weaviate 1.14.0, where all objects are namespaced
        by class name.
        STRONGLY recommended to set it with Weaviate >= 1.14.0. It will be required in future
        versions of Weaviate Server and Clients. Use None value ONLY for Weaviate < v1.14.0,
        by default None
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
        if self.to_object_class_name is not None:
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
class Error:
    message: str
    code: Optional[int] = None
    original_uuid: Optional[UUID] = None


@dataclass
class _BatchReturn:
    """This class contains the results of a batch `insert_many` operation.

    Since the individual objects within the batch can error for differing reasons, the data is split up within this class for ease use when performing error checking, handling, and data revalidation.

    Attributes:
        all_responses: A list of all the responses from the batch operation. Each response is either a `uuid_package.UUID` object or an `Error` object.
        uuids: A dictionary of all the successful responses from the batch operation. The keys are the indices of the objects in the batch, and the values are the `uuid_package.UUID` objects.
        errors: A dictionary of all the failed responses from the batch operation. The keys are the indices of the objects in the batch, and the values are the `Error` objects.
        has_errors: A boolean indicating whether or not any of the objects in the batch failed to be inserted. If this is `True`, then the `errors` dictionary will contain at least one entry.
    """

    all_responses: List[Union[uuid_package.UUID, Error]]
    uuids: Dict[int, uuid_package.UUID]
    errors: Dict[int, Error]
    elapsed_seconds: float
    has_errors: bool = False

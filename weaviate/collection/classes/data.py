import uuid as uuid_package
from dataclasses import dataclass
from typing import List, Optional, Dict, Union, Generic

from weaviate.collection.classes.internal import Properties
from weaviate.types import UUID


@dataclass
class Error:
    """This class represents an error that occurred when attempting to insert an object within a batch."""

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
    has_errors: bool = False


@dataclass
class RefError:
    """This class represents an error that occurred when attempting to insert a reference between objects within a batch."""

    message: str


@dataclass
class BatchReference:
    """This class represents a reference between objects to be used when batching."""

    from_uuid: UUID
    to_uuid: UUID


@dataclass
class DataObject(Generic[Properties]):
    """This class represents an entire object within a collection to be used when batching."""

    properties: Properties
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None

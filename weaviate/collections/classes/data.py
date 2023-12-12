from dataclasses import dataclass
from typing import List, Optional, Generic
from weaviate.collections.classes.internal import Properties, References, CrossReference
from weaviate.types import UUID


@dataclass
class Error:
    """This class represents an error that occurred when attempting to insert an object within a batch."""

    message: str
    code: Optional[int] = None
    original_uuid: Optional[UUID] = None


@dataclass
class RefError:
    """This class represents an error that occurred when attempting to insert a reference between objects within a batch."""

    message: str


@dataclass
class DataObject(Generic[Properties]):
    """This class represents an entire object within a collection to be used when batching."""

    properties: Optional[Properties] = None
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None


@dataclass
class DataReference(Generic[Properties, References]):
    """This class represents a reference between objects within a collection to be used when batching."""

    from_property: str
    from_uuid: UUID
    to: CrossReference[Properties, References]

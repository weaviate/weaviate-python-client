from dataclasses import dataclass
from typing import Any, Generic, List, Optional
from typing_extensions import TypeVar
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


P = TypeVar("P", bound=Optional[Any], covariant=True, default=None)
R = TypeVar("R", bound=Optional[Any], covariant=True, default=None)


@dataclass
class DataObject(Generic[P, R]):
    """This class represents an entire object within a collection to be used when batching."""

    properties: P = None  # type: ignore
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None
    references: R = None  # type: ignore
    # R is clearly bounded to Optional[Any] and defaults to None but mypy doesn't seem to understand that
    # throws error: Incompatible types in assignment (expression has type "None", variable has type "R")  [assignment]


@dataclass
class DataReference:
    """This class represents a reference between objects within a collection to be used when batching."""

    from_property: str
    from_uuid: UUID
    to_uuid: UUID

from dataclasses import dataclass
from typing import Any, Generic, List, Optional, Union
from typing_extensions import TypeVar, TypeAlias
from weaviate.types import BEACON, UUID, VECTORS

import uuid as uuid_package


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
    vector: Optional[VECTORS] = None
    references: R = None  # type: ignore
    # R is clearly bounded to Optional[Any] and defaults to None but mypy doesn't seem to understand that
    # throws error: Incompatible types in assignment (expression has type "None", variable has type "R")  [assignment]


@dataclass
class _DataReference:
    from_property: str
    from_uuid: UUID
    to_uuid: Union[UUID, List[UUID]]

    def _to_uuids(self) -> List[UUID]:
        if isinstance(self.to_uuid, uuid_package.UUID) or isinstance(self.to_uuid, str):
            return [self.to_uuid]
        else:
            return self.to_uuid


@dataclass
class DataReferenceMulti(_DataReference):
    """This class represents a reference between objects within a collection to be used when batching."""

    target_collection: str

    def _to_beacons(self) -> List[str]:
        return [f"{BEACON}{self.target_collection}/{uuid}" for uuid in self._to_uuids()]


@dataclass
class DataReference(_DataReference):
    """This class represents a reference between objects within a collection to be used when batching."""

    MultiTarget = DataReferenceMulti

    def _to_beacons(self) -> List[str]:
        return [f"{BEACON}{uuid}" for uuid in self._to_uuids()]


DataReferences: TypeAlias = Union[DataReference, DataReferenceMulti]

import uuid as uuid_package
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional
from typing_extensions import TypeVar

from weaviate.weaviate_types import UUID

Properties = TypeVar("Properties")


@dataclass
class _MetadataReturn:
    # uuid: Optional[uuid_package.UUID] = Field(None, alias="id")
    # vector: Optional[List[float]] = None
    # creation_time_unix: Optional[int] = Field(None, alias="creationTimeUnix")
    # last_update_time_unix: Optional[int] = Field(None, alias="lastUpdateTimeUnix")
    # distance: Optional[float] = None
    # certainty: Optional[float] = None
    # score: Optional[float] = None
    # explain_score: Optional[str] = Field(None, alias="explainScore")
    # is_consistent: Optional[bool] = Field(None, alias="isConsistent")
    uuid: Optional[uuid_package.UUID] = None
    vector: Optional[List[float]] = None
    creation_time_unix: Optional[int] = None
    last_update_time_unix: Optional[int] = None
    distance: Optional[float] = None
    certainty: Optional[float] = None
    score: Optional[float] = None
    explain_score: Optional[str] = None
    is_consistent: Optional[bool] = None


@dataclass
class _Object(Generic[Properties]):
    data: Properties
    metadata: _MetadataReturn


def _metadata_from_dict(metadata: Dict[str, Any]) -> _MetadataReturn:
    return _MetadataReturn(
        uuid=uuid_package.UUID(metadata["id"]) if "id" in metadata else None,
        vector=metadata.get("vector"),
        creation_time_unix=metadata.get("creationTimeUnix"),
        last_update_time_unix=metadata.get("lastUpdateTimeUnix"),
        distance=metadata.get("distance"),
        certainty=metadata.get("certainty"),
        explain_score=metadata.get("explainScore"),
        score=metadata.get("score"),
        is_consistent=metadata.get("isConsistent"),
    )


@dataclass
class BatchReference:
    from_uuid: UUID
    to_uuid: UUID


@dataclass
class DataObject:
    data: Dict[str, Any]
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None

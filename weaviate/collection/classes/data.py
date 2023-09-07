from dataclasses import dataclass
from typing import List, Optional, Dict, Generic

from pydantic import BaseModel, Field
from weaviate.collection.classes.internal import P
from weaviate.util import _to_beacons
from weaviate.weaviate_types import UUID, UUIDS


class IncludesModel(BaseModel):
    def to_include(self) -> str:
        include: List[str] = []
        for field, value in self:
            if value:
                include.append(field)
        return ",".join(include)


class GetObjectByIdMetadata(IncludesModel):
    classification: bool = False
    vector: bool = False


class GetObjectsMetadata(IncludesModel):
    classification: bool = False
    featureProjection: bool = Field(False, alias="feature_projection")
    vector: bool = False


@dataclass
class ReferenceTo:
    uuids: UUIDS

    @property
    def uuids_str(self) -> List[str]:
        if isinstance(self.uuids, list):
            return [str(uid) for uid in self.uuids]
        else:
            return [str(self.uuids)]

    def to_beacons(self) -> List[Dict[str, str]]:
        return _to_beacons(self.uuids)


@dataclass
class ReferenceToMultiTarget(ReferenceTo):
    target_collection: str

    def to_beacons(self) -> List[Dict[str, str]]:
        return _to_beacons(self.uuids, self.target_collection)


@dataclass
class DataObject(Generic[P]):
    properties: P
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None


@dataclass
class DataReference:
    from_property: str
    from_uuid: UUID
    to_uuid: UUID

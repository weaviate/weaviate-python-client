import uuid as uuid_package
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Mapping, Optional
from typing_extensions import TypeVar

from weaviate.util import _to_beacons
from weaviate.weaviate_types import UUIDS

Properties = TypeVar("Properties", bound=Mapping[str, Any], default=Dict[str, Any])

P = TypeVar("P")


@dataclass
class _MetadataReturn:
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
class _Object(Generic[P]):
    properties: P
    metadata: _MetadataReturn


class Reference(Generic[P]):
    def __init__(self, objects: Optional[List[_Object[P]]], uuids: Optional[UUIDS]):
        self.objects = objects
        self.__uuids = uuids

    @classmethod
    def to(cls, uuids: UUIDS) -> "Reference[P]":
        return cls(None, uuids)

    def to_beacons(self) -> List[Dict[str, str]]:
        return _to_beacons(self.__uuids)

    @classmethod
    def _from(cls, objects: List[_Object[P]]) -> "Reference[P]":
        return cls(objects, None)


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


def _extract_props_from_list_of_objects(type_: Any) -> Optional[Any]:
    """Extract inner type from List[_Object[Properties]]"""
    if getattr(type_, "__origin__", None) == List:
        inner_type = type_.__args__[0]
        if getattr(inner_type, "__origin__", None) == _Object:
            return inner_type.__args__[0]
    return None


def _extract_props_from_reference(type_: Reference[P]) -> Optional[P]:
    """Extract inner type from Reference[Properties]"""
    if getattr(type_, "__origin__", None) == Reference:
        return type_.__args__[0]
    return None

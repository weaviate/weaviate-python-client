import sys
import uuid as uuid_package
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Union, get_origin, get_type_hints

if sys.version_info < (3, 9):
    from typing_extensions import Annotated
else:
    from typing import Annotated

from weaviate.collection.classes.grpc import LinkTo, LinkToMultiTarget, MetadataQuery, PROPERTIES
from weaviate.collection.classes.types import Properties, P
from weaviate.util import _to_beacons
from weaviate.weaviate_types import UUIDS


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
    def __init__(
        self,
        objects: Optional[List[_Object[P]]],
        target_collection: Optional[str],
        uuids: Optional[UUIDS],
    ):
        self.objects = objects
        self.__target_collection = target_collection if target_collection else ""
        self.__uuids = uuids

    @classmethod
    def to(cls, uuids: UUIDS) -> "Reference[P]":
        return cls(None, None, uuids)

    @classmethod
    def to_multi_target(cls, uuids: UUIDS, target_collection: str) -> "Reference[P]":
        return cls(None, target_collection, uuids)

    def _to_beacons(self) -> List[Dict[str, str]]:
        return _to_beacons(self.__uuids, self.__target_collection)

    @classmethod
    def _from(cls, objects: List[_Object[P]]) -> "Reference[P]":
        return cls(objects, None, None)

    @property
    def is_multi_target(self) -> bool:
        return self.__target_collection != ""

    @property
    def uuids_str(self) -> List[str]:
        if isinstance(self.__uuids, list):
            return [str(uid) for uid in self.__uuids]
        else:
            return [str(self.__uuids)]

    @property
    def target_collection(self) -> str:
        return self.__target_collection


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


def _extract_property_type_from_reference(type_: Reference[P]) -> Optional[P]:
    """Extract inner type from Reference[Properties]"""
    if getattr(type_, "__origin__", None) == Reference:
        return type_.__args__[0]
    return None


def __create_link_to_from_annotated_reference(
    link_on: str,
    value: Union[
        Annotated[Reference[Properties], MetadataQuery],
        Annotated[Reference[Properties], MetadataQuery, str],
    ],
) -> Union[LinkTo, LinkToMultiTarget, None]:
    """Create LinkTo or LinkToMultiTarget from Annotated[Reference[Properties]]"""
    if get_origin(value) is Annotated:
        inner_type = value.__args__[0]
        metadata = value.__metadata__[0]
        if get_origin(inner_type) is Reference:
            try:
                target_collection = value.__metadata__[1]
                return LinkToMultiTarget(
                    link_on=link_on,
                    metadata=metadata,
                    properties=_extract_properties_from_data_model(
                        _extract_property_type_from_reference(inner_type)
                    ),
                    target_collection=target_collection,
                )
            except IndexError:
                return LinkTo(
                    link_on=link_on,
                    metadata=metadata,
                    properties=_extract_properties_from_data_model(
                        _extract_property_type_from_reference(inner_type)
                    ),
                )


def _extract_properties_from_data_model(type_: Properties) -> PROPERTIES:
    """Extract properties of Properties recursively from Properties"""
    return [
        __create_link_to_from_annotated_reference(key, value)
        if get_origin(value) is Annotated
        else key
        for key, value in get_type_hints(type_, include_extras=True).items()
    ]

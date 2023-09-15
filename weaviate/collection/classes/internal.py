import sys
from dataclasses import dataclass
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, Union, cast

import uuid as uuid_package

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_type_hints, get_origin
else:
    from typing import Annotated, get_type_hints, get_origin

from weaviate.collection.collection_base import CollectionObjectBase
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
    generative: Optional[str] = None


@dataclass
class _Object(Generic[P]):
    properties: P
    metadata: _MetadataReturn


@dataclass
class _GenerativeReturn(Generic[P]):
    objects: List[_Object[P]]
    generated: Optional[str] = None


@dataclass
class _QueryReturn(Generic[P]):
    objects: List[_Object[P]]


class ReferenceFactory(Generic[P]):
    def __init__(
        self,
        objects: Optional[List[_Object[P]]],
        target_collection: Optional[str],
        uuids: Optional[UUIDS],
    ):
        self.__objects = objects
        self.__target_collection = target_collection if target_collection else ""
        self.__uuids = uuids

    @classmethod
    def to(cls, uuids: UUIDS) -> "ReferenceFactory[P]":
        return cls(None, None, uuids)

    @classmethod
    def to_multi_target(
        cls, uuids: UUIDS, target_collection: Union[str, CollectionObjectBase]
    ) -> "ReferenceFactory[P]":
        return cls(
            None,
            target_collection.name
            if isinstance(target_collection, CollectionObjectBase)
            else target_collection,
            uuids,
        )

    def _to_beacons(self) -> List[Dict[str, str]]:
        if self.__uuids is None:
            return []
        return _to_beacons(self.__uuids, self.__target_collection)

    @classmethod
    def _from(cls, objects: List[_Object[P]]) -> "ReferenceFactory[P]":
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

    @property
    def objects(self) -> List[_Object[P]]:
        return self.__objects or []


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


def _extract_property_type_from_reference(type_: ReferenceFactory[P]) -> Type[P]:
    """Extract inner type from Reference[Properties]"""
    if getattr(type_, "__origin__", None) == ReferenceFactory:
        args = cast(List[Type[P]], getattr(type_, "__args__", None))
        return args[0]
    raise ValueError("Type is not Reference[Properties]")


def _extract_property_type_from_annotated_reference(
    type_: Union[
        Annotated[ReferenceFactory[P], MetadataQuery],
        Annotated[ReferenceFactory[P], MetadataQuery, str],
    ]
) -> Type[P]:
    """Extract inner type from Annotated[Reference[Properties]]"""
    if get_origin(type_) is Annotated:
        args = cast(List[ReferenceFactory[Type[P]]], getattr(type_, "__args__", None))
        inner_type = args[0]
        if get_origin(inner_type) is ReferenceFactory:
            inner_args = cast(List[Type[P]], getattr(inner_type, "__args__", None))
            return inner_args[0]
    raise ValueError("Type is not Annotated[Reference[Properties]]")


def __create_link_to_from_annotated_reference(
    link_on: str,
    value: Union[
        Annotated[ReferenceFactory[Properties], MetadataQuery],
        Annotated[ReferenceFactory[Properties], MetadataQuery, str],
    ],
) -> Union[LinkTo, LinkToMultiTarget]:
    """Create LinkTo or LinkToMultiTarget from Annotated[Reference[Properties]]"""
    assert get_origin(value) is Annotated
    args = cast(List[ReferenceFactory[Properties]], getattr(value, "__args__", None))
    inner_type = args[0]
    assert get_origin(inner_type) is ReferenceFactory
    inner_type_metadata = cast(
        Union[Tuple[MetadataQuery], Tuple[MetadataQuery, str]], getattr(value, "__metadata__", None)
    )
    metadata = inner_type_metadata[0]
    if len(inner_type_metadata) == 2:
        target_collection = cast(Tuple[MetadataQuery, str], inner_type_metadata)[
            1
        ]  # https://github.com/python/mypy/issues/1178
        return LinkToMultiTarget(
            link_on=link_on,
            return_metadata=metadata,
            return_properties=_extract_properties_from_data_model(
                _extract_property_type_from_annotated_reference(value)
            ),
            target_collection=target_collection,
        )
    else:
        return LinkTo(
            link_on=link_on,
            return_metadata=metadata,
            return_properties=_extract_properties_from_data_model(
                _extract_property_type_from_annotated_reference(value)
            ),
        )


def __create_link_to_from_reference(
    link_on: str,
    value: ReferenceFactory[Properties],
) -> LinkTo:
    """Create LinkTo from Reference[Properties]"""
    return LinkTo(
        link_on=link_on,
        return_metadata=MetadataQuery(),
        return_properties=_extract_properties_from_data_model(
            _extract_property_type_from_reference(value)
        ),
    )


def _extract_properties_from_data_model(type_: Type[Properties]) -> PROPERTIES:
    """Extract properties of Properties recursively from Properties"""
    return [
        __create_link_to_from_annotated_reference(key, value)
        if get_origin(value) is Annotated
        else (
            __create_link_to_from_reference(key, value)
            if get_origin(value) is ReferenceFactory
            else key
        )
        for key, value in get_type_hints(type_, include_extras=True).items()
    ]

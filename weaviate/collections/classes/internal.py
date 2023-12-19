import datetime
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Mapping, Optional, Tuple, Type, Union, cast
from typing_extensions import TypeAlias, TypeVar, is_typeddict

import uuid as uuid_package

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_type_hints, get_origin, get_args
else:
    from typing import Annotated, get_type_hints, get_origin, get_args

from weaviate.collections.base import _CollectionBase
from weaviate.collections.classes.grpc import (
    FromNested,
    FromReference,
    FromReferenceMultiTarget,
    Generate,
    MetadataQuery,
    METADATA,
    PROPERTIES,
    REFERENCES,
)
from weaviate.collections.classes.types import Properties, P, R, TProperties, WeaviateProperties
from weaviate.exceptions import WeaviateQueryException, InvalidDataModelException
from weaviate.util import _to_beacons
from weaviate.types import UUIDS

from weaviate.proto.v1 import search_get_pb2


IReferences = TypeVar("IReferences", bound=Optional[Mapping[str, Any]], default=None)


@dataclass
class _MetadataResult:
    uuid: Optional[uuid_package.UUID]
    vector: Optional[List[float]]
    creation_time_unix: Optional[int]
    last_update_time_unix: Optional[int]
    distance: Optional[float]
    certainty: Optional[float]
    score: Optional[float]
    explain_score: Optional[str]
    is_consistent: Optional[bool]
    generative: Optional[str]


def _metadata_from_dict(
    metadata: Dict[str, Any]
) -> Tuple[uuid_package.UUID, Optional[List[float]], "_MetadataReturn"]:
    uuid = uuid_package.UUID(metadata["id"]) if "id" in metadata else None
    if uuid is None:
        raise WeaviateQueryException("The query returned an object with an empty ID string")
    return (
        uuid,
        metadata.get("vector"),
        _MetadataReturn(
            creation_time=metadata.get("creationTimeUnix"),
            last_update_time=metadata.get("lastUpdateTimeUnix"),
            distance=metadata.get("distance"),
            certainty=metadata.get("certainty"),
            explain_score=metadata.get("explainScore"),
            score=metadata.get("score"),
            is_consistent=metadata.get("isConsistent"),
        ),
    )


@dataclass
class _MetadataReturn:
    creation_time: Optional[datetime.datetime] = None
    last_update_time: Optional[datetime.datetime] = None
    distance: Optional[float] = None
    certainty: Optional[float] = None
    score: Optional[float] = None
    explain_score: Optional[str] = None
    is_consistent: Optional[bool] = None

    def _is_empty(self) -> bool:
        return all(
            [
                self.creation_time is None,
                self.last_update_time is None,
                self.distance is None,
                self.certainty is None,
                self.score is None,
                self.explain_score is None,
                self.is_consistent is None,
            ]
        )


@dataclass
class _Object(Generic[P, R]):
    uuid: uuid_package.UUID
    metadata: _MetadataReturn
    properties: P
    references: R
    vector: Optional[List[float]]


@dataclass
class _MetadataSingleObjectReturn:
    creation_time: datetime.datetime
    last_update_time: datetime.datetime
    is_consistent: Optional[bool]


@dataclass
class _ObjectSingleReturn(Generic[P, R]):
    uuid: uuid_package.UUID
    metadata: _MetadataSingleObjectReturn
    properties: P
    references: R
    vector: Optional[List[float]]


@dataclass
class _GroupByObject(Generic[P, R], _Object[P, R]):
    belongs_to_group: str


@dataclass
class _GenerativeObject(Generic[P, R], _Object[P, R]):
    generated: Optional[str]


@dataclass
class _GenerativeReturn(Generic[P, R]):
    objects: List[_GenerativeObject[P, R]]
    generated: Optional[str]


@dataclass
class _GroupByResult(Generic[P, R]):
    name: str
    min_distance: float
    max_distance: float
    number_of_objects: int
    objects: List[_Object[P, R]]


@dataclass
class _GroupByReturn(Generic[P, R]):
    objects: List[_GroupByObject[P, R]]
    groups: Dict[str, _GroupByResult[P, R]]


@dataclass
class _QueryReturn(Generic[P, R]):
    objects: List[_Object[P, R]]


_GQLEntryReturnType: TypeAlias = Dict[str, List[Dict[str, Any]]]


@dataclass
class _RawGQLReturn:
    aggregate: _GQLEntryReturnType
    explore: _GQLEntryReturnType
    get: _GQLEntryReturnType
    errors: Optional[Dict[str, Any]]


class _Generative:
    single: Optional[str]
    grouped: Optional[str]
    grouped_properties: Optional[List[str]]

    def __init__(
        self,
        single: Optional[str],
        grouped: Optional[str],
        grouped_properties: Optional[List[str]],
    ) -> None:
        self.single = single
        self.grouped = grouped
        self.grouped_properties = grouped_properties

    def to_grpc(self) -> search_get_pb2.GenerativeSearch:
        return search_get_pb2.GenerativeSearch(
            single_response_prompt=self.single,
            grouped_response_task=self.grouped,
            grouped_properties=self.grouped_properties,
        )

    @classmethod
    def from_input(cls, generate: Optional[Generate]) -> Optional["_Generative"]:
        return (
            cls(
                single=generate.single_prompt,
                grouped=generate.grouped_task,
                grouped_properties=generate.grouped_properties,
            )
            if generate
            else None
        )


class _GroupBy:
    prop: str
    number_of_groups: int
    objects_per_group: int

    def __init__(self, prop: str, number_of_groups: int, objects_per_group: int) -> None:
        self.prop = prop
        self.number_of_groups = number_of_groups
        self.objects_per_group = objects_per_group

    def to_grpc(self) -> search_get_pb2.GroupBy:
        return search_get_pb2.GroupBy(
            path=[self.prop],
            number_of_groups=self.number_of_groups,
            objects_per_group=self.objects_per_group,
        )


Nested = Annotated[P, "NESTED"]


def __is_nested(value: Any) -> bool:
    return (
        get_origin(value) is Annotated
        and len(get_args(value)) == 2
        and cast(str, get_args(value)[1]) == "NESTED"
    )


def __create_nested_property_from_nested(name: str, value: Any) -> FromNested:
    if not __is_nested(value):
        raise ValueError(
            f"Non nested property detected in generic resolution, {value} of type {type(value)} is not allowed as a nested property."
        )
    inner_type = get_args(value)[0]
    return FromNested(
        name=name,
        properties=[
            __create_nested_property_from_nested(key, val) if __is_nested(val) else key
            for key, val in get_type_hints(inner_type, include_extras=True).items()
        ],
    )


class _Reference:
    def __init__(
        self,
        target_collection: Optional[str],
        uuids: Optional[UUIDS],
    ):
        """You should not initialise this class directly. Use the `.to()` or `.to_multi_target()` class methods instead."""
        self.__target_collection = target_collection if target_collection else ""
        self.__uuids = uuids

    def _to_beacons(self) -> List[Dict[str, str]]:
        if self.__uuids is None:
            return []
        return _to_beacons(self.__uuids, self.__target_collection)

    @property
    def is_multi_target(self) -> bool:
        """Returns True if the reference is to a multi-target collection."""
        return self.__target_collection != ""

    @property
    def uuids_str(self) -> List[str]:
        """Returns the UUIDs as strings."""
        if isinstance(self.__uuids, list):
            return [str(uid) for uid in self.__uuids]
        else:
            return [str(self.__uuids)]

    @property
    def target_collection(self) -> str:
        """Returns the target collection name."""
        return self.__target_collection


class _CrossReference(Generic[Properties, IReferences]):
    def __init__(
        self,
        objects: Optional[List[_Object[Properties, IReferences]]],
    ):
        self.__objects = objects

    @classmethod
    def _from(
        cls, objects: List[_Object[Properties, IReferences]]
    ) -> "_CrossReference[Properties, IReferences]":
        return cls(objects)

    @property
    def objects(self) -> List[_Object[Properties, IReferences]]:
        """Returns the objects of the cross reference."""
        return self.__objects or []


CrossReference: TypeAlias = _CrossReference[Properties, IReferences]
"""Use this TypeAlias when you want to type hint a cross reference within a generic data model.

If you want to define a reference property when creating your collection, use `ReferenceProperty` or `ReferencePropertyMultiTarget` instead.

If you want to create a reference when inserting an object, use `Reference.to()` or `Reference.to_multi_target()` instead.

Example:
    >>> import typing
    >>> import weaviate.classes as wvc
    >>>
    >>> class One(typing.TypedDict):
    ...     prop: str
    >>>
    >>> class Two(typing.TypedDict):
    ...     one: wvc.CrossReference[One]
"""

CrossReferences = Mapping[str, _CrossReference[WeaviateProperties, "CrossReferences"]]


class Reference:
    """Factory class for cross references to other objects.

    Can be used with or without generics. If used with generics, the type of the cross reference can be defined from
    which the nested relationship will be used when performing queries using the generics. If used without generics,
    all returned objects will of the`Dict[str, Any]` type.
    """

    @classmethod
    def to(
        cls,
        uuids: UUIDS,
    ) -> "_Reference":
        """Define cross references to other objects by their UUIDs.

        Can be made to be generic by supplying a type to the `data_model` argument.

        Arguments:
            `uuids`
                List of UUIDs of the objects to which the reference should point.
        """
        return _Reference(None, uuids)

    @classmethod
    def to_multi_target(
        cls,
        uuids: UUIDS,
        target_collection: Union[str, _CollectionBase],
    ) -> "_Reference":
        """Define cross references to other objects by their UUIDs and the collection in which they are stored.

        Can be made to be generic by supplying a type to the `data_model` argument.

        Arguments:
            `uuids`
                List of UUIDs of the objects to which the reference should point.
            `target_collection`
                The collection in which the objects are stored. Can be either the name of the collection or the collection object itself.
        """
        return _Reference(
            target_collection.name
            if isinstance(target_collection, _CollectionBase)
            else target_collection,
            uuids,
        )


WeaviateReference: TypeAlias = _Reference
WeaviateReferences: TypeAlias = Mapping[str, WeaviateReference]


@dataclass
class CrossReferenceAnnotation:
    """Dataclass to be used when annotating a generic cross reference property with options for retrieving data from the cross referenced object when querying.

    Example:
        >>> import typing
        >>> import weaviate.classes as wvc
        >>>
        >>> class One(typing.TypedDict):
        ...     prop: str
        >>>
        >>> class Two(typing.TypedDict):
        ...     one: typing.Annotated[
        ...         wvc.CrossReference[One],
        ...         wvc.CrossReferenceAnnotation(include_vector=True)
        ...     ]
    """

    include_vector: bool = field(default=False)
    metadata: Optional[MetadataQuery] = field(default=None)
    target_collection: Optional[str] = field(default=None)


ReferenceAnnotation = CrossReferenceAnnotation
"""@deprecated: Use `CrossReferenceAnnotation` instead."""


def _extract_types_from_reference(
    type_: CrossReference[Properties, "References"]
) -> Tuple[Type[Properties], Type["References"]]:
    """Extract first inner type from CrossReference[Properties, References]."""
    if get_origin(type_) == _CrossReference:
        return cast(Tuple[Type[Properties], Type[References]], get_args(type_))
    raise ValueError("Type is not CrossReference[Properties, References]")


def _extract_types_from_annotated_reference(
    type_: Annotated[CrossReference[Properties, "References"], ReferenceAnnotation]
) -> Tuple[Type[Properties], Type["References"]]:
    """Extract inner type from Annotated[CrossReference[Properties, References]]."""
    if get_origin(type_) is Annotated:
        args = get_args(type_)
        inner_type = cast(CrossReference[Properties, References], args[0])
        return _extract_types_from_reference(inner_type)
    raise ValueError("Type is not Annotated[CrossReference[Properties, References]]")


def __is_annotated_reference(value: Any) -> bool:
    return (
        get_origin(value) is Annotated
        and len(get_args(value)) == 2
        and get_origin(get_args(value)[0]) is _CrossReference
    )


def __create_link_to_from_annotated_reference(
    link_on: str, value: Annotated[CrossReference[Properties, "References"], ReferenceAnnotation]
) -> Union[FromReference, FromReferenceMultiTarget]:
    """Create FromReference or FromReferenceMultiTarget from Annotated[CrossReference[Properties], ReferenceAnnotation]."""
    assert get_origin(value) is Annotated
    args = cast(List[CrossReference[Properties, References]], get_args(value))
    inner_type = args[0]
    assert get_origin(inner_type) is _CrossReference
    inner_type_metadata = cast(Tuple[ReferenceAnnotation], getattr(value, "__metadata__", None))
    annotation = inner_type_metadata[0]
    types = _extract_types_from_annotated_reference(value)
    print(annotation)
    if annotation.target_collection is not None:
        return FromReferenceMultiTarget(
            link_on=link_on,
            include_vector=annotation.include_vector,
            return_metadata=annotation.metadata,
            return_properties=_extract_properties_from_data_model(types[0]),
            return_references=_extract_references_from_data_model(types[1]),
            target_collection=annotation.target_collection,
        )
    else:
        return FromReference(
            link_on=link_on,
            include_vector=annotation.include_vector,
            return_metadata=annotation.metadata,
            return_properties=_extract_properties_from_data_model(types[0]),
            return_references=_extract_references_from_data_model(types[1]),
        )


def __is_reference(value: Any) -> bool:
    return get_origin(value) is _CrossReference


def __create_link_to_from_reference(
    link_on: str,
    value: CrossReference[Properties, "References"],
) -> FromReference:
    """Create FromReference from CrossReference[Properties]."""
    types = _extract_types_from_annotated_reference(value)
    return FromReference(
        link_on=link_on,
        return_properties=_extract_properties_from_data_model(types[0]),
        return_references=_extract_references_from_data_model(types[1]),
    )


def _extract_properties_from_data_model(type_: Type[Properties]) -> PROPERTIES:
    """Extract properties of Properties recursively from Properties.

    Checks to see if there is a _Reference[Properties], Annotated[_Reference[Properties]], or _Nested[Properties]
    in the data model and lists out the properties as classes readily consumable by the underlying API.
    """
    return [
        __create_nested_property_from_nested(key, value) if __is_nested(value) else key
        for key, value in get_type_hints(type_, include_extras=True).items()
    ]


def _extract_references_from_data_model(type_: Type["References"]) -> Optional[REFERENCES]:
    """Extract references of References recursively from References.

    Checks to see if there is a _Reference[References], Annotated[_Reference[References]], or _Nested[References]
    in the data model and lists out the references as classes readily consumable by the underlying API.
    """
    refs = [
        __create_link_to_from_annotated_reference(key, value)
        if __is_annotated_reference(value)
        else __create_link_to_from_reference(key, value)
        for key, value in get_type_hints(type_, include_extras=True).items()
    ]
    return refs if len(refs) > 0 else None


References = TypeVar("References", bound=Optional[Mapping[str, Any]], default=None)
"""`References` is used wherever a single generic type is needed for references"""

# I wish we could have bound=Mapping[str, CrossReference["P", "R"]] here, but you can't have generic bounds, so Any must suffice
TReferences = TypeVar("TReferences", bound=Mapping[str, Any])
"""`TReferences` is used alongside `References` wherever there are two generic types needed"""


def _check_references_generic(references: Optional[Type["References"]]) -> None:
    if (
        references is not None
        and get_origin(references) is not dict
        and not is_typeddict(references)
    ):
        raise InvalidDataModelException("references")


ReturnProperties: TypeAlias = Union[PROPERTIES, Type[TProperties]]
ReturnReferences: TypeAlias = Union[Union[FromReference, List[FromReference]], Type[TReferences]]


@dataclass
class _QueryOptions(Generic[Properties, References, TReferences]):
    include_metadata: bool
    include_properties: bool
    include_references: bool
    include_vector: bool

    @classmethod
    def from_input(
        cls,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[Properties]],
        include_vector: bool,
        collection_references: Optional[Type[References]],
        query_references: Optional[ReturnReferences[TReferences]],
    ) -> "_QueryOptions":
        return cls(
            include_metadata=return_metadata is not None,
            include_properties=not (
                isinstance(return_properties, list) and len(return_properties) == 0
            ),
            include_references=collection_references is not None or query_references is not None,
            include_vector=include_vector,
        )

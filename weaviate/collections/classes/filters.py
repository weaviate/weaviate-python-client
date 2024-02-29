import uuid as uuid_lib

from datetime import datetime
from enum import Enum
from typing import List, Optional, Union
from typing_extensions import TypeAlias
from pydantic import Field
from weaviate.collections.classes.types import GeoCoordinate


from weaviate.collections.classes.types import _WeaviateInput
from weaviate.types import UUID
from weaviate.proto.v1 import base_pb2
from weaviate.util import get_valid_uuid

from weaviate.exceptions import WeaviateInvalidInputError


class _Operator(str, Enum):
    EQUAL = "Equal"
    NOT_EQUAL = "NotEqual"
    LESS_THAN = "LessThan"
    LESS_THAN_EQUAL = "LessThanEqual"
    GREATER_THAN = "GreaterThan"
    GREATER_THAN_EQUAL = "GreaterThanEqual"
    LIKE = "Like"
    IS_NULL = "IsNull"
    CONTAINS_ANY = "ContainsAny"
    CONTAINS_ALL = "ContainsAll"
    WITHIN_GEO_RANGE = "WithinGeoRange"
    AND = "And"
    OR = "Or"

    def _to_grpc(self) -> base_pb2.Filters.Operator:
        if self == _Operator.EQUAL:
            return base_pb2.Filters.OPERATOR_EQUAL
        elif self == _Operator.NOT_EQUAL:
            return base_pb2.Filters.OPERATOR_NOT_EQUAL
        elif self == _Operator.LESS_THAN:
            return base_pb2.Filters.OPERATOR_LESS_THAN
        elif self == _Operator.LESS_THAN_EQUAL:
            return base_pb2.Filters.OPERATOR_LESS_THAN_EQUAL
        elif self == _Operator.GREATER_THAN:
            return base_pb2.Filters.OPERATOR_GREATER_THAN
        elif self == _Operator.GREATER_THAN_EQUAL:
            return base_pb2.Filters.OPERATOR_GREATER_THAN_EQUAL
        elif self == _Operator.LIKE:
            return base_pb2.Filters.OPERATOR_LIKE
        elif self == _Operator.IS_NULL:
            return base_pb2.Filters.OPERATOR_IS_NULL
        elif self == _Operator.CONTAINS_ANY:
            return base_pb2.Filters.OPERATOR_CONTAINS_ANY
        elif self == _Operator.CONTAINS_ALL:
            return base_pb2.Filters.OPERATOR_CONTAINS_ALL
        elif self == _Operator.WITHIN_GEO_RANGE:
            return base_pb2.Filters.OPERATOR_WITHIN_GEO_RANGE
        elif self == _Operator.AND:
            return base_pb2.Filters.OPERATOR_AND
        else:
            assert self == _Operator.OR
            return base_pb2.Filters.OPERATOR_OR


class _Filters:
    def __and__(self, other: "_Filters") -> "_FilterAnd":
        return _FilterAnd([self, other])

    def __or__(self, other: "_Filters") -> "_FilterOr":
        return _FilterOr([self, other])


class _FilterAnd(_Filters):
    def __init__(self, filters: List[_Filters]):
        self.filters: List[_Filters] = filters

    # replace with the following once 3.11 is the minimum version
    #     Operator: weaviate_pb2.Filters.OperatorType = weaviate_pb2.Filters.OperatorAnd
    @property
    def operator(self) -> _Operator:
        return _Operator.AND


class _FilterOr(_Filters):
    def __init__(self, filters: List[_Filters]):
        self.filters: List[_Filters] = filters

    # replace with the following once 3.11 is the minimum version
    #     Operator: weaviate_pb2.Filters.OperatorType = weaviate_pb2.Filters.OperatorOr
    @property
    def operator(self) -> _Operator:
        return _Operator.OR


class _GeoCoordinateFilter(GeoCoordinate):
    distance: float


FilterValuesList = Union[
    List[str], List[bool], List[int], List[float], List[datetime], List[uuid_lib.UUID]
]
FilterValues = Union[
    int, float, str, bool, datetime, UUID, _GeoCoordinateFilter, None, FilterValuesList
]


class _SingleTargetRef(_WeaviateInput):
    link_on: str
    target: Optional["_FilterTargets"] = Field(exclude=True, default=None)


class _MultiTargetRef(_WeaviateInput):
    target_collection: str
    link_on: str
    target: Optional["_FilterTargets"] = Field(exclude=True, default=None)


class _CountRef(_WeaviateInput):
    link_on: str


_TargetRefs = Union[_SingleTargetRef, _MultiTargetRef]
_FilterTargets = Union[_SingleTargetRef, _MultiTargetRef, _CountRef, str]


class _FilterValue(_Filters, _WeaviateInput):
    value: FilterValues
    operator: _Operator
    target: _FilterTargets


class _FilterBase:
    _target: Optional[_TargetRefs] = None
    _property: Union[str, _CountRef]

    def _target_path(self) -> _FilterTargets:
        if self._target is None:
            return self._property

        # get last element in chain
        target = self._target
        while target.target is not None:
            assert isinstance(target.target, _MultiTargetRef) or isinstance(
                target.target, _SingleTargetRef
            )
            target = target.target

        target.target = self._property
        return self._target


class _FilterByProperty(_FilterBase):
    def __init__(self, prop: str, length: bool, target: Optional[_TargetRefs] = None) -> None:
        self._target = target
        if length:
            prop = "len(" + prop + ")"

        self._property = prop

    def is_none(self, val: bool) -> _FilterValue:
        """Filter on whether the property is `None`."""
        return _FilterValue(
            target=self._target_path(),
            value=val,
            operator=_Operator.IS_NULL,
        )

    def contains_any(self, val: FilterValuesList) -> _FilterValue:
        """Filter on whether the property contains any of the given values."""
        if len(val) == 0:
            raise WeaviateInvalidInputError("Filter contains_any must have at least one value")
        return _FilterValue(
            target=self._target_path(),
            value=val,
            operator=_Operator.CONTAINS_ANY,
        )

    def contains_all(self, val: FilterValuesList) -> _FilterValue:
        """Filter on whether the property contains all of the given values."""
        if len(val) == 0:
            raise WeaviateInvalidInputError("Filter contains_all must have at least one value")

        return _FilterValue(
            target=self._target_path(),
            value=val,
            operator=_Operator.CONTAINS_ALL,
        )

    def equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is equal to the given value."""
        return _FilterValue(target=self._target_path(), value=val, operator=_Operator.EQUAL)

    def not_equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is not equal to the given value."""
        return _FilterValue(target=self._target_path(), value=val, operator=_Operator.NOT_EQUAL)

    def less_than(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is less than the given value."""
        return _FilterValue(target=self._target_path(), value=val, operator=_Operator.LESS_THAN)

    def less_or_equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is less than or equal to the given value."""
        return _FilterValue(
            target=self._target_path(),
            value=val,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is greater than the given value."""
        return _FilterValue(
            target=self._target_path(),
            value=val,
            operator=_Operator.GREATER_THAN,
        )

    def greater_or_equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is greater than or equal to the given value."""
        return _FilterValue(
            target=self._target_path(),
            value=val,
            operator=_Operator.GREATER_THAN_EQUAL,
        )

    def like(self, val: str) -> _FilterValue:
        """Filter on whether the property is like the given value.

        This filter can make use of `*` and `?` as wildcards. See [the docs](https://weaviate.io/developers/weaviate/search/filters#by-partial-matches-text) for more details.
        """
        return _FilterValue(target=self._target_path(), value=val, operator=_Operator.LIKE)

    def within_geo_range(self, coordinate: GeoCoordinate, distance: float) -> _FilterValue:
        """Filter on whether the property is within a given range of a geo-coordinate.

        See [the docs](https://weaviate.io/developers/weaviate/search/filters##by-geo-coordinates) for more details.
        """
        return _FilterValue(
            target=self._target_path(),
            value=_GeoCoordinateFilter(
                latitude=coordinate.latitude, longitude=coordinate.longitude, distance=distance
            ),
            operator=_Operator.WITHIN_GEO_RANGE,
        )


class _FilterByTime(_FilterBase):
    def contains_any(self, dates: List[datetime]) -> _FilterValue:
        """Filter for objects with the given time.

        Arguments:
            `dates`
                List of dates to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(),
            value=dates,
            operator=_Operator.CONTAINS_ANY,
        )

    def equal(self, date: datetime) -> _FilterValue:
        """Filter on whether the creation time is equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(),
            value=date,
            operator=_Operator.EQUAL,
        )

    def not_equal(self, date: datetime) -> _FilterValue:
        """Filter on whether the creation time is not equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(),
            value=date,
            operator=_Operator.NOT_EQUAL,
        )

    def less_than(self, date: datetime) -> _FilterValue:
        """Filter on whether the creation time is less than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(),
            value=date,
            operator=_Operator.LESS_THAN,
        )

    def less_or_equal(self, date: datetime) -> _FilterValue:
        """Filter on whether the creation time is less than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(),
            value=date,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, date: datetime) -> _FilterValue:
        """Filter on whether the creation time is greater than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(),
            value=date,
            operator=_Operator.GREATER_THAN,
        )

    def greater_or_equal(self, date: datetime) -> _FilterValue:
        """Filter on whether the creation time is greater than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue(
            target=self._target_path(), value=date, operator=_Operator.GREATER_THAN_EQUAL
        )


class _FilterByUpdateTime(_FilterByTime):
    def __init__(self, target: Optional[_TargetRefs] = None) -> None:
        self._target = target
        self._property = "_lastUpdateTimeUnix"


class _FilterByCreationTime(_FilterByTime):
    def __init__(self, target: Optional[_TargetRefs] = None) -> None:
        self._target = target
        self._property = "_creationTimeUnix"


class _FilterById(_FilterBase):
    def __init__(self, target: Optional[_TargetRefs] = None) -> None:
        self._target = target
        self._property = "_id"

    def contains_any(self, uuids: List[UUID]) -> _FilterValue:
        """Filter for objects that has one of the given ID."""
        if len(uuids) == 0:
            raise WeaviateInvalidInputError("Filter contains_any must have at least one value")
        return _FilterValue(
            target=self._target_path(),
            value=[get_valid_uuid(val) for val in uuids],
            operator=_Operator.CONTAINS_ANY,
        )

    def equal(self, uuid: UUID) -> _FilterValue:
        """Filter for object that has the given ID."""
        return _FilterValue(
            target=self._target_path(),
            value=get_valid_uuid(uuid),
            operator=_Operator.EQUAL,
        )

    def not_equal(self, uuid: UUID) -> _FilterValue:
        """Filter our object that has the given ID."""
        return _FilterValue(
            target=self._target_path(),
            value=get_valid_uuid(uuid),
            operator=_Operator.NOT_EQUAL,
        )


class _FilterByCount(_FilterBase):
    def __init__(self, link_on: str, target: Optional[_TargetRefs] = None) -> None:
        self._target = target
        self._property = _CountRef(link_on=link_on)

    def equal(self, count: int) -> _FilterValue:
        """Filter on whether the number of references is equal to the given integer.

        Arguments:
            `count`
                count to filter on.
        """
        return _FilterValue(
            target=self._target_path(),
            value=count,
            operator=_Operator.EQUAL,
        )

    def not_equal(self, count: int) -> _FilterValue:
        """Filter on whether the number of references is equal to the given integer.

        Arguments:
            `count`
                count to filter on.
        """
        return _FilterValue(
            target=self._target_path(),
            value=count,
            operator=_Operator.NOT_EQUAL,
        )

    def less_than(self, count: int) -> _FilterValue:
        """Filter on whether the number of references is equal to the given integer.

        Arguments:
            `count`
                count to filter on.
        """
        return _FilterValue(
            target=self._target_path(),
            value=count,
            operator=_Operator.LESS_THAN,
        )

    def less_or_equal(self, count: int) -> _FilterValue:
        """Filter on whether the number of references is equal to the given integer.

        Arguments:
            `count`
                count to filter on.
        """
        return _FilterValue(
            target=self._target_path(),
            value=count,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, count: int) -> _FilterValue:
        """Filter on whether the number of references is equal to the given integer.

        Arguments:
            `count`
                count to filter on.
        """
        return _FilterValue(
            target=self._target_path(),
            value=count,
            operator=_Operator.GREATER_THAN,
        )

    def greater_or_equal(self, count: int) -> _FilterValue:
        """Filter on whether the number of references is equal to the given integer.

        Arguments:
            `count`
                count to filter on.
        """
        return _FilterValue(
            target=self._target_path(), value=count, operator=_Operator.GREATER_THAN_EQUAL
        )


class _FilterByRef:
    def __init__(self, target: _TargetRefs) -> None:
        self.__target = target
        self.__last_target = self.__target  # use this to append to the end of the chain

    def by_ref(self, link_on: str) -> "_FilterByRef":
        """Filter on the given reference."""
        self.__last_target.target = _SingleTargetRef(link_on=link_on)
        self.__last_target = self.__last_target.target
        return self

    def by_ref_multi_target(self, reference: str, target_collection: str) -> "_FilterByRef":
        """Filter on the given multi-target reference."""
        self.__last_target.target = _MultiTargetRef(
            link_on=reference, target_collection=target_collection
        )
        self.__last_target = self.__last_target.target

        return self

    def by_ref_count(self, link_on: str) -> _FilterByCount:
        """Filter on the given reference."""
        return _FilterByCount(link_on, self.__target)

    def by_id(self) -> _FilterById:
        """Define a filter based on the uuid to be used when querying and deleting from a collection."""
        return _FilterById(self.__target)

    def by_creation_time(self) -> _FilterByCreationTime:
        """Define a filter based on the creation time to be used when querying and deleting from a collection."""
        return _FilterByCreationTime(self.__target)

    def by_update_time(self) -> _FilterByUpdateTime:
        """Define a filter based on the update time to be used when querying and deleting from a collection."""
        return _FilterByUpdateTime(self.__target)

    def by_property(self, name: str, length: bool = False) -> _FilterByProperty:
        """Define a filter based on a property to be used when querying and deleting from a collection."""
        return _FilterByProperty(prop=name, length=length, target=self.__target)


class Filter:
    """This class is used to define filters to be used when querying and deleting from a collection.

    It forms the root of a method chaining hierarchy that allows you to iteratively define filters that can
    hop between objects through references in a formulaic way.

    See [the docs](https://weaviate.io/developers/weaviate/search/filters) for more information.
    """

    def __init__(self) -> None:
        raise TypeError("Filter cannot be instantiated. Use the static methods to create a filter.")

    @staticmethod
    def by_ref(link_on: str) -> _FilterByRef:
        """Define a filter based on a reference to be used when querying and deleting from a collection."""
        return _FilterByRef(_SingleTargetRef(link_on=link_on))

    @staticmethod
    def by_ref_multi_target(link_on: str, target_collection: str) -> _FilterByRef:
        """Define a filter based on a reference to be used when querying and deleting from a collection."""
        return _FilterByRef(_MultiTargetRef(link_on=link_on, target_collection=target_collection))

    @staticmethod
    def by_ref_count(link_on: str) -> _FilterByCount:
        """Define a filter based on the number of references to be used when querying and deleting from a collection."""
        return _FilterByCount(link_on=link_on)

    @staticmethod
    def by_id() -> _FilterById:
        """Define a filter based on the uuid to be used when querying and deleting from a collection."""
        return _FilterById(None)

    @staticmethod
    def by_creation_time() -> _FilterByCreationTime:
        """Define a filter based on the creation time to be used when querying and deleting from a collection."""
        return _FilterByCreationTime(target=None)

    @staticmethod
    def by_update_time() -> _FilterByUpdateTime:
        """Define a filter based on the update time to be used when querying and deleting from a collection."""
        return _FilterByUpdateTime(target=None)

    @staticmethod
    def by_property(name: str, length: bool = False) -> _FilterByProperty:
        """Define a filter based on a property to be used when querying and deleting from a collection."""
        return _FilterByProperty(prop=name, length=length, target=None)

    @staticmethod
    def all_of(filters: List[_Filters]) -> _Filters:
        """Combine all filters in the input list with an AND operator."""
        if len(filters) == 1:
            return filters[0]
        elif len(filters) == 0:
            raise WeaviateInvalidInputError("Filter.all_of must have at least one filter")
        return _FilterAnd(filters)

    @staticmethod
    def any_of(filters: List[_Filters]) -> _Filters:
        """Combine all filters in the input list with an OR operator."""
        if len(filters) == 1:
            return filters[0]
        elif len(filters) == 0:
            raise WeaviateInvalidInputError("Filter.any_of must have at least one filter")
        return _FilterOr(filters)


# type aliases for return classes
FilterByProperty: TypeAlias = _FilterByProperty
FilterById: TypeAlias = _FilterById
FilterByCreationTime: TypeAlias = _FilterByCreationTime
FilterByUpdateTime: TypeAlias = _FilterByUpdateTime
FilterByRef: TypeAlias = _FilterByRef
FilterReturn: TypeAlias = _Filters

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
from weaviate.warnings import _Warnings


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
        elif self == _Operator.OR:
            return base_pb2.Filters.OPERATOR_OR
        else:
            raise ValueError(f"Unknown operator {self}")


class _Filters:
    def __and__(self, other: "_Filters") -> "_FilterAnd":
        return _FilterAnd(self, other)

    def __or__(self, other: "_Filters") -> "_FilterOr":
        return _FilterOr(self, other)


class _FilterAnd(_Filters):
    def __init__(self, *args: _Filters):
        self.filters: List[_Filters] = list(args)

    # replace with the following once 3.11 is the minimum version
    #     Operator: weaviate_pb2.Filters.OperatorType = weaviate_pb2.Filters.OperatorAnd
    @property
    def operator(self) -> _Operator:
        return _Operator.AND


class _FilterOr(_Filters):
    def __init__(self, *args: _Filters):
        self.filters: List[_Filters] = list(args)

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


class _FilterValue(_Filters, _WeaviateInput):
    path: Union[str, List[str]]
    value: FilterValues
    operator: _Operator


class _FilterOld:
    """Define a filter based on a property to be used when querying and deleting from a collection.

    Use the `__init__` method to define the path to the property to be filtered on and then
    use the methods of this class to define the condition to filter on.

    To combine multiple filters, you can use `&` or `|` operators for each `AND` or `OR` operations, e.g.,
        `Filter("name").equal("John") & Filter("age").greater_than(18)`

    See [the docs](https://weaviate.io/developers/weaviate/search/filters) for more details!
    """

    def __init__(self, path: Union[str, List[str]], length: bool = False):
        """Initialise the filter.

        Arguments:
            `path`
                The path to the property to be filtered on.
                    This can be a single string in the case of a top-level property or a list of strings in the case of a nested cross-ref property.
            `length`
                If `True`, the length of the property will be used in the filter. Defaults to `False`.
                    This is only valid for properties of type `string` or `text`. The inverted index must also be configured to index the property length.
        """
        _Warnings.old_filter_by_property()
        if isinstance(path, str):
            path = [path]
        if length:
            path[-1] = "len(" + path[-1] + ")"
        self.__internal_path = path

    def is_none(self, val: bool) -> _FilterValue:
        """Filter on whether the property is `None`."""
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.IS_NULL)

    def contains_any(self, val: FilterValuesList) -> _FilterValue:
        """Filter on whether the property contains any of the given values."""
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.CONTAINS_ANY,
        )

    def contains_all(self, val: FilterValuesList) -> _FilterValue:
        """Filter on whether the property contains all of the given values."""
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.CONTAINS_ALL,
        )

    def equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is equal to the given value."""
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.EQUAL)

    def not_equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is not equal to the given value."""
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.NOT_EQUAL)

    def less_than(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is less than the given value."""
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.LESS_THAN)

    def less_or_equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is less than or equal to the given value."""
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is greater than the given value."""
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.GREATER_THAN,
        )

    def greater_or_equal(self, val: FilterValues) -> _FilterValue:
        """Filter on whether the property is greater than or equal to the given value."""
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.GREATER_THAN_EQUAL,
        )

    def like(self, val: str) -> _FilterValue:
        """Filter on whether the property is like the given value.

        This filter can make use of `*` and `?` as wildcards. See [the docs](https://weaviate.io/developers/weaviate/search/filters#by-partial-matches-text) for more details.
        """
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.LIKE)

    def within_geo_range(self, coordinate: GeoCoordinate, distance: float) -> _FilterValue:
        """Filter on whether the property is within a given range of a geo-coordinate.

        See [the docs](https://weaviate.io/developers/weaviate/search/filters#by-geolocation) for more details.
        """
        return _FilterValue(
            path=self.__internal_path,
            value=_GeoCoordinateFilter(
                latitude=coordinate.latitude, longitude=coordinate.longitude, distance=distance
            ),
            operator=_Operator.WITHIN_GEO_RANGE,
        )


class _FilterId:
    @staticmethod
    def contains_any(
        uuids: List[UUID], on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter for objects that has one of the given ID."""
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=_FilterId._prepare_path(path=on_reference_path),
            value=[get_valid_uuid(val) for val in uuids],
            operator=_Operator.CONTAINS_ANY,
        )

    @staticmethod
    def equal(uuid: UUID, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter for object that has the given ID."""
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=_FilterId._prepare_path(path=on_reference_path),
            value=get_valid_uuid(uuid),
            operator=_Operator.EQUAL,
        )

    @staticmethod
    def not_equal(uuid: UUID, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter our object that has the given ID."""
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=_FilterId._prepare_path(path=on_reference_path),
            value=get_valid_uuid(uuid),
            operator=_Operator.NOT_EQUAL,
        )

    @staticmethod
    def _prepare_path(path: Optional[List[str]]) -> List[str]:
        return path or [] + ["_id"]


class _FilterTime:
    @staticmethod
    def contains_any(dates: List[datetime], on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=dates,
            operator=_Operator.CONTAINS_ANY,
        )

    @staticmethod
    def equal(date: datetime, on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=date,
            operator=_Operator.EQUAL,
        )

    @staticmethod
    def not_equal(date: datetime, on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=date,
            operator=_Operator.NOT_EQUAL,
        )

    @staticmethod
    def less_than(date: datetime, on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=date,
            operator=_Operator.LESS_THAN,
        )

    @staticmethod
    def less_or_equal(date: datetime, on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=date,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    @staticmethod
    def greater_than(date: datetime, on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=date,
            operator=_Operator.GREATER_THAN,
        )

    @staticmethod
    def greater_or_equal(date: datetime, on_reference_path: List[str]) -> _FilterValue:
        _Warnings.old_filter_by_metadata()
        return _FilterValue(
            path=on_reference_path,
            value=date,
            operator=_Operator.GREATER_THAN_EQUAL,
        )


class _FilterCreationTime(_FilterTime):
    @staticmethod
    def contains_any(
        dates: List[datetime], on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter for objects that have been created at the given time.

        Arguments:
            `dates`
                List of dates to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.contains_any(dates, _FilterCreationTime._prepare_path(on_reference_path))

    @staticmethod
    def equal(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the creation time is equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.equal(date, _FilterCreationTime._prepare_path(on_reference_path))

    @staticmethod
    def not_equal(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the creation time is not equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.not_equal(date, _FilterCreationTime._prepare_path(on_reference_path))

    @staticmethod
    def less_than(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the creation time is less than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.less_than(date, _FilterCreationTime._prepare_path(on_reference_path))

    @staticmethod
    def less_or_equal(
        date: datetime, on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter on whether the creation time is less than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.less_or_equal(date, _FilterCreationTime._prepare_path(on_reference_path))

    @staticmethod
    def greater_than(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the creation time is greater than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.greater_than(date, _FilterCreationTime._prepare_path(on_reference_path))

    @staticmethod
    def greater_or_equal(
        date: datetime, on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter on whether the creation time is greater than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.greater_or_equal(
            date, _FilterCreationTime._prepare_path(on_reference_path)
        )

    @staticmethod
    def _prepare_path(path: Optional[List[str]]) -> List[str]:
        return path or [] + ["_creationTimeUnix"]


class _FilterUpdateTime:
    @staticmethod
    def contains_any(
        dates: List[datetime], on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter for objects that have been last update at the given time.

        Arguments:
            `dates`
                List of dates to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.contains_any(dates, _FilterUpdateTime._prepare_path(on_reference_path))

    @staticmethod
    def equal(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the last update time is equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.equal(date, _FilterUpdateTime._prepare_path(on_reference_path))

    @staticmethod
    def not_equal(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the last update time is not equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.not_equal(date, _FilterUpdateTime._prepare_path(on_reference_path))

    @staticmethod
    def less_than(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the last update time is less than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.less_than(date, _FilterUpdateTime._prepare_path(on_reference_path))

    @staticmethod
    def less_or_equal(
        date: datetime, on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter on whether the last update time is less than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.less_or_equal(date, _FilterUpdateTime._prepare_path(on_reference_path))

    @staticmethod
    def greater_than(date: datetime, on_reference_path: Optional[List[str]] = None) -> _FilterValue:
        """Filter on whether the last update time is greater than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.greater_than(date, _FilterUpdateTime._prepare_path(on_reference_path))

    @staticmethod
    def greater_or_equal(
        date: datetime, on_reference_path: Optional[List[str]] = None
    ) -> _FilterValue:
        """Filter on whether the last update time is greater than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterTime.greater_or_equal(
            date, _FilterUpdateTime._prepare_path(on_reference_path)
        )

    @staticmethod
    def _prepare_path(path: Optional[List[str]]) -> List[str]:
        return path or [] + ["_lastUpdateTimeUnix"]


class FilterMetadata:
    """Define a filter based on a ID, Creation- or LastUpdateTime  to be used when querying a collection.

    To combine multiple filters, you can use `&` or `|` operators for each `AND` or `OR` operations, e.g.,
        `FilterMetadata.FilterById.equal(UUID) & Filter("age").greater_than(18)`

    See [the docs](https://weaviate.io/developers/weaviate/search/filters) for more details!
    """

    ById = _FilterId
    ByCreationTime = _FilterCreationTime
    ByUpdateTime = _FilterUpdateTime


class _SingleTargetRef(_WeaviateInput):
    link_on: str
    target: Optional["_FilterTargets"] = Field(exclude=True, default=None)


class _MultiTargetRef(_WeaviateInput):
    target_collection: str
    link_on: str
    target: Optional["_FilterTargets"] = Field(exclude=True, default=None)


_TargetRefs = Union[_SingleTargetRef, _MultiTargetRef]
_FilterTargets = Union[_SingleTargetRef, _MultiTargetRef, str]


class _FilterValue2(_Filters, _WeaviateInput):
    value: FilterValues
    operator: _Operator
    target: _FilterTargets


class _FilterBase:
    _target: Optional[_TargetRefs] = None
    _property: str

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

    def is_none(self, val: bool) -> _FilterValue2:
        """Filter on whether the property is `None`."""
        return _FilterValue2(
            target=self._target_path(),
            value=val,
            operator=_Operator.IS_NULL,
        )

    def contains_any(self, val: FilterValuesList) -> _FilterValue2:
        """Filter on whether the property contains any of the given values."""
        return _FilterValue2(
            target=self._target_path(),
            value=val,
            operator=_Operator.CONTAINS_ANY,
        )

    def contains_all(self, val: FilterValuesList) -> _FilterValue2:
        """Filter on whether the property contains all of the given values."""
        return _FilterValue2(
            target=self._target_path(),
            value=val,
            operator=_Operator.CONTAINS_ALL,
        )

    def equal(self, val: FilterValues) -> _FilterValue2:
        """Filter on whether the property is equal to the given value."""
        return _FilterValue2(target=self._target_path(), value=val, operator=_Operator.EQUAL)

    def not_equal(self, val: FilterValues) -> _FilterValue2:
        """Filter on whether the property is not equal to the given value."""
        return _FilterValue2(target=self._target_path(), value=val, operator=_Operator.NOT_EQUAL)

    def less_than(self, val: FilterValues) -> _FilterValue2:
        """Filter on whether the property is less than the given value."""
        return _FilterValue2(target=self._target_path(), value=val, operator=_Operator.LESS_THAN)

    def less_or_equal(self, val: FilterValues) -> _FilterValue2:
        """Filter on whether the property is less than or equal to the given value."""
        return _FilterValue2(
            target=self._target_path(),
            value=val,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, val: FilterValues) -> _FilterValue2:
        """Filter on whether the property is greater than the given value."""
        return _FilterValue2(
            target=self._target_path(),
            value=val,
            operator=_Operator.GREATER_THAN,
        )

    def greater_or_equal(self, val: FilterValues) -> _FilterValue2:
        """Filter on whether the property is greater than or equal to the given value."""
        return _FilterValue2(
            target=self._target_path(),
            value=val,
            operator=_Operator.GREATER_THAN_EQUAL,
        )

    def like(self, val: str) -> _FilterValue2:
        """Filter on whether the property is like the given value.

        This filter can make use of `*` and `?` as wildcards. See [the docs](https://weaviate.io/developers/weaviate/search/filters#by-partial-matches-text) for more details.
        """
        return _FilterValue2(target=self._target_path(), value=val, operator=_Operator.LIKE)

    def within_geo_range(self, coordinate: GeoCoordinate, distance: float) -> _FilterValue2:
        """Filter on whether the property is within a given range of a geo-coordinate.

        See [the docs](https://weaviate.io/developers/weaviate/search/filters#by-geolocation) for more details.
        """
        return _FilterValue2(
            target=self._target_path(),
            value=_GeoCoordinateFilter(
                latitude=coordinate.latitude, longitude=coordinate.longitude, distance=distance
            ),
            operator=_Operator.WITHIN_GEO_RANGE,
        )


class _FilterByTime(_FilterBase):
    def contains_any(self, dates: List[datetime]) -> _FilterValue2:
        """Filter for objects with the given time.

        Arguments:
            `dates`
                List of dates to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
            target=self._target_path(),
            value=dates,
            operator=_Operator.CONTAINS_ANY,
        )

    def equal(self, date: datetime) -> _FilterValue2:
        """Filter on whether the creation time is equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
            target=self._target_path(),
            value=date,
            operator=_Operator.EQUAL,
        )

    def not_equal(self, date: datetime) -> _FilterValue2:
        """Filter on whether the creation time is not equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
            target=self._target_path(),
            value=date,
            operator=_Operator.NOT_EQUAL,
        )

    def less_than(self, date: datetime) -> _FilterValue2:
        """Filter on whether the creation time is less than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
            target=self._target_path(),
            value=date,
            operator=_Operator.LESS_THAN,
        )

    def less_or_equal(self, date: datetime) -> _FilterValue2:
        """Filter on whether the creation time is less than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
            target=self._target_path(),
            value=date,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, date: datetime) -> _FilterValue2:
        """Filter on whether the creation time is greater than the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
            target=self._target_path(),
            value=date,
            operator=_Operator.GREATER_THAN,
        )

    def greater_or_equal(self, date: datetime) -> _FilterValue2:
        """Filter on whether the creation time is greater than or equal to the given time.

        Arguments:
            `date`
                date to filter on.
            `on_reference_path`
                If the filter is on a cross-ref property, the path to the property to be filtered on, example: on_reference_path=["ref_property", "target_collection"].
        """
        return _FilterValue2(
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

    def contains_any(self, uuids: List[UUID]) -> _FilterValue2:
        """Filter for objects that has one of the given ID."""
        return _FilterValue2(
            target=self._target_path(),
            value=[get_valid_uuid(val) for val in uuids],
            operator=_Operator.CONTAINS_ANY,
        )

    def equal(self, uuid: UUID) -> _FilterValue2:
        """Filter for object that has the given ID."""
        return _FilterValue2(
            target=self._target_path(),
            value=get_valid_uuid(uuid),
            operator=_Operator.EQUAL,
        )

    def not_equal(self, uuid: UUID) -> _FilterValue2:
        """Filter our object that has the given ID."""
        return _FilterValue2(
            target=self._target_path(),
            value=get_valid_uuid(uuid),
            operator=_Operator.NOT_EQUAL,
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

    def by_id(self) -> _FilterById:
        """Define a filter based on the uuid to be used when querying and deleting from a collection."""
        return _FilterById(self.__target)

    def by_creation_time(self) -> _FilterByCreationTime:
        """Define a filter based on the creation time to be used when querying and deleting from a collection."""
        return _FilterByCreationTime(self.__target)

    def by_update_time(self) -> _FilterByUpdateTime:
        """Define a filter based on the update time to be used when querying and deleting from a collection."""
        return _FilterByUpdateTime(self.__target)

    def by_property(self, prop: str, length: bool = False) -> _FilterByProperty:
        """Define a filter based on a property to be used when querying and deleting from a collection."""
        return _FilterByProperty(prop=prop, length=length, target=self.__target)


class Filter(_FilterOld):
    """Filter class."""

    @staticmethod
    def by_ref(link_on: str) -> _FilterByRef:
        """Define a filter based on a reference to be used when querying and deleting from a collection."""
        return _FilterByRef(_SingleTargetRef(link_on=link_on))

    @staticmethod
    def by_ref_multi_target(link_on: str, target_collection: str) -> _FilterByRef:
        """Define a filter based on a reference to be used when querying and deleting from a collection."""
        return _FilterByRef(_MultiTargetRef(link_on=link_on, target_collection=target_collection))

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
    def by_property(prop: str, length: bool = False) -> _FilterByProperty:
        """Define a filter based on a property to be used when querying and deleting from a collection."""
        return _FilterByProperty(prop=prop, length=length, target=None)


# type aliases for return classes
FilterByProperty: TypeAlias = _FilterByProperty
FilterById: TypeAlias = _FilterById
FilterByCreationTime: TypeAlias = _FilterByCreationTime
FilterByUpdateTime: TypeAlias = _FilterByUpdateTime
FilterByRef: TypeAlias = _FilterByRef

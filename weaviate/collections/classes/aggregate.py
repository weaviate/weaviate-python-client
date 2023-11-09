from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Protocol,
    Union,
    overload,
)
from typing_extensions import TypeVar

from pydantic import BaseModel, Field

from weaviate.collections.classes.config import DataType

N = TypeVar("N", int, float)


@dataclass
class AggregateInt:
    """The aggregation result for an integer property."""

    count: Optional[int]
    maximum: Optional[int]
    mean: Optional[float]
    median: Optional[int]
    mode: Optional[int]
    sum_: Optional[int]


@dataclass
class AggregateFloat:
    """The aggregation result for a float property."""

    count: Optional[int]
    maximum: Optional[float]
    mean: Optional[float]
    median: Optional[float]
    mode: Optional[float]
    sum_: Optional[float]


@dataclass
class TopOccurrence:
    """The top occurrence of a string property."""

    occurs: Optional[int]
    value: Optional[str]


@dataclass
class AggregateStr:
    """The aggregation result for a string property."""

    count: Optional[int]
    top_occurrences: Optional[List[TopOccurrence]]


@dataclass
class AggregateBool:
    """The aggregation result for a boolean property."""

    count: Optional[int]
    percentage_false: Optional[float]
    percentage_true: Optional[float]
    total_false: Optional[int]
    total_true: Optional[int]


@dataclass
class AggregateRef:
    """The aggregation result for a cross-reference property."""

    pointing_to: Optional[str]


@dataclass
class AggregateDate:
    """The aggregation result for a date property."""

    count: Optional[int]
    maximum: Optional[str]
    median: Optional[str]
    minimum: Optional[str]
    mode: Optional[str]


AggregateResult = Union[
    AggregateInt, AggregateFloat, AggregateStr, AggregateBool, AggregateDate, AggregateRef
]

AProperties = Dict[str, AggregateResult]


@dataclass
class _AggregateReturn:
    properties: AProperties
    total_count: Optional[int]


@dataclass
class _GroupedBy:
    prop: str
    value: str


@dataclass
class _AggregateGroupByReturn:
    grouped_by: _GroupedBy
    properties: AProperties
    total_count: Optional[int]


class _MetricsBase(BaseModel):
    property_name: str
    count: bool = Field(default=False)
    type_: bool = Field(default=False)


class _MetricsStr(_MetricsBase):
    top_occurrences_count: bool = Field(default=False)
    top_occurrences_value: bool = Field(default=False)

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
                "type" if self.type_ else "",
                "topOccurrences {"
                if self.top_occurrences_count or self.top_occurrences_value
                else "",
                "occurs" if self.top_occurrences_count else "",
                "value" if self.top_occurrences_value else "",
                "}" if self.top_occurrences_count or self.top_occurrences_value else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


class _MetricsNumber(_MetricsBase):
    maximum: bool = Field(default=False)
    mean: bool = Field(default=False)
    median: bool = Field(default=False)
    minimum: bool = Field(default=False)
    mode: bool = Field(default=False)
    sum_: bool = Field(default=False)

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
                "type" if self.type_ else "",
                "maximum" if self.maximum else "",
                "mean" if self.mean else "",
                "median" if self.median else "",
                "minimum" if self.minimum else "",
                "mode" if self.mode else "",
                "sum" if self.sum_ else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


class _MetricsInt(_MetricsNumber):
    pass


class _MetricsFloat(_MetricsNumber):
    pass


class _MetricsBool(_MetricsBase):
    percentage_false: bool = Field(default=False)
    percentage_true: bool = Field(default=False)
    total_false: bool = Field(default=False)
    total_true: bool = Field(default=False)

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
                "type" if self.type_ else "",
                "percentageFalse" if self.percentage_false else "",
                "percentageTrue" if self.percentage_true else "",
                "totalFalse" if self.total_false else "",
                "totalTrue" if self.total_true else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


class _MetricsDate(_MetricsBase):
    maximum: bool = Field(default=False)
    median: bool = Field(default=False)
    minimum: bool = Field(default=False)
    mode: bool = Field(default=False)

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
                "type" if self.type_ else "",
                "maximum" if self.maximum else "",
                "median" if self.median else "",
                "minimum" if self.minimum else "",
                "mode" if self.mode else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


class _MetricsRef(BaseModel):
    property_name: str
    pointing_to: bool = Field(default=False)
    type_: bool = Field(default=False)

    def to_gql(self) -> str:
        body = " ".join(
            [
                "pointingTo" if self.pointing_to else "",
                "type" if self.type_ else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


_Metrics = Union[
    _MetricsStr,
    _MetricsInt,
    _MetricsFloat,
    _MetricsDate,
    _MetricsBool,
    _MetricsRef,
]

PropertiesMetrics = List[_Metrics]


class SupportsReturningStr(Protocol):
    """An interface for the `returning` method of the `Metrics` class for string properties."""

    def returning(
        self,
        count: bool = False,
        top_occurrences_count: bool = False,
        top_occurrences_value: bool = False,
    ) -> _MetricsStr:
        """Define the metrics to be returned for a string property when aggregating over a collection.

        Arguments:
            `count`
                Whether to include the number of objects that contain this property.
            `top_occurrences_count`
                Whether to include the number of the top occurrences of a property's value.
            `top_occurrences_value`
                Whether to include the value of the top occurrences of a property's value.

        Returns:
            A `_MetricsStr` object that includes the metrics to be returned.
        """
        ...


class SupportsReturningInt(Protocol):
    """An interface for the `returning` method of the `Metrics` class for integer properties."""

    def returning(
        self,
        count: bool = False,
        maximum: bool = False,
        mean: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
        sum_: bool = False,
    ) -> _MetricsInt:
        """Define the metrics to be returned for an integer property when aggregating over a collection.

        Arguments:
            `count`
                Whether to include the number of objects that contain this property.
            `maximum`
                Whether to include the maximum value of this property.
            `mean`
                Whether to include the mean value of this property.
            `median`
                Whether to include the median value of this property.
            `minimum`
                Whether to include the minimum value of this property.
            `mode`
                Whether to include the mode value of this property.
            `sum_`
                Whether to include the sum of this property.

        Returns:
            A `_MetricsInt` object that includes the metrics to be returned.
        """
        ...


class SupportsReturningFloat(Protocol):
    """An interface for the `returning` method of the `Metrics` class for float properties."""

    def returning(
        self,
        count: bool = False,
        maximum: bool = False,
        mean: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
        sum_: bool = False,
    ) -> _MetricsFloat:
        """Define the metrics to be returned for a float property when aggregating over a collection.

        Arguments:
            `count`
                Whether to include the number of objects that contain this property.
            `maximum`
                Whether to include the maximum value of this property.
            `mean`
                Whether to include the mean value of this property.
            `median`
                Whether to include the median value of this property.
            `minimum`
                Whether to include the minimum value of this property.
            `mode`
                Whether to include the mode value of this property.
            `sum_`
                Whether to include the sum of this property.

        Returns:
            A `_MetricsFloat` object that includes the metrics to be returned.
        """
        ...


class SupportsReturningBool(Protocol):
    """An interface for the `returning` method of the `Metrics` class for boolean properties."""

    def returning(
        self,
        count: bool = False,
        percentage_false: bool = False,
        percentage_true: bool = False,
        total_false: bool = False,
        total_true: bool = False,
    ) -> _MetricsBool:
        """Define the metrics to be returned for a boolean property when aggregating over a collection.

        Arguments:
            `count`
                Whether to include the number of objects that contain this property.
            `percentage_false`
                Whether to include the percentage of objects that have a false value for this property.
            `percentage_true`
                Whether to include the percentage of objects that have a true value for this property.
            `total_false`
                Whether to include the total number of objects that have a false value for this property.
            `total_true`
                Whether to include the total number of objects that have a true value for this property.

        Returns:
            A `_MetricsBool` object that includes the metrics to be returned.
        """
        ...


class SupportsReturningDate(Protocol):
    """An interface for the `returning` method of the `Metrics` class for date properties."""

    def returning(
        self,
        count: bool = False,
        maximum: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
    ) -> _MetricsDate:
        """Define the metrics to be returned for a date property when aggregating over a collection.

        Arguments:
            `count`
                Whether to include the number of objects that contain this property.
            `maximum`
                Whether to include the maximum value of this property.
            `median`
                Whether to include the median value of this property.
            `minimum`
                Whether to include the minimum value of this property.
            `mode`
                Whether to include the mode value of this property.

        Returns:
            A `_MetricsDate` object that includes the metrics to be returned.
        """
        ...


class SupportsReturningRef(Protocol):
    """An interface for the `returning` method of the `Metrics` class for cross-reference properties."""

    def returning(
        self,
        pointing_to: bool = False,
    ) -> _MetricsRef:
        """Define the metrics to be returned for a cross-reference property when aggregating over a collection.

        Arguments:
            `pointing_to`
                Whether to include the collection names that this property references.

        Returns:
            A `_MetricsRef` object that includes the metrics to be returned.
        """
        ...


# type ignore all the overloads of __new__ here because mypy is not capable of understanding that the return type is a protocol (interface)
# that the class (type) implements since Aggregate inherits from all the returned protocols
class Metrics(
    SupportsReturningStr,
    SupportsReturningInt,
    SupportsReturningFloat,
    SupportsReturningBool,
    SupportsReturningDate,
    SupportsReturningRef,
):
    """Define the metrics to be returned based on a property when aggregating over a collection.

    Use the `__init__` method to define the name to the property to be aggregated on and
    its data type using `weaviate.classes.DataType` or `"cref"` if the property is a cross-reference
    then use the methods of this class to define the specific available metrics to be returned.

    See [the docs](https://weaviate.io/developers/weaviate/search/aggregate) for more details!
    """

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.TEXT]) -> SupportsReturningStr:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.TEXT_ARRAY]) -> SupportsReturningStr:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.INT]) -> SupportsReturningInt:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.INT_ARRAY]) -> SupportsReturningInt:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.NUMBER]) -> SupportsReturningFloat:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.NUMBER_ARRAY]) -> SupportsReturningFloat:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.BOOL]) -> SupportsReturningBool:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.BOOL_ARRAY]) -> SupportsReturningBool:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.DATE]) -> SupportsReturningDate:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal[DataType.DATE_ARRAY]) -> SupportsReturningDate:  # type: ignore
        ...

    @overload
    def __new__(cls, property_: str, type_: Literal["cref"]) -> SupportsReturningRef:  # type: ignore
        ...

    def __new__(cls, property_: str, type_: Union[DataType, Literal["cref"]]) -> "Metrics":
        """Create a new `Metrics` object."""
        return super().__new__(cls)

    def __init__(self, property_: str, type_: Union[DataType, Literal["cref"]]) -> None:
        self.__property = property_
        self.__type = type_

    def returning(self, **kwargs) -> _Metrics:  # type: ignore
        """Define the metrics to be returned for a property when aggregating over a collection.

        If you're seeing this docstring then you've likely forgotten to define the data type of the property.

        Example:
            ```python
            import weaviate.classes as wvc
            wvc.Metrics("myProperty", DataType.TEXT).returning(count=True)
            ```
        """
        if self.__type == DataType.TEXT or self.__type == DataType.TEXT_ARRAY:
            return self.__str(**kwargs)
        elif self.__type == DataType.INT or self.__type == DataType.INT_ARRAY:
            return self.__int(**kwargs)
        elif self.__type == DataType.NUMBER or self.__type == DataType.NUMBER_ARRAY:
            return self.__float(**kwargs)
        elif self.__type == DataType.BOOL or self.__type == DataType.BOOL_ARRAY:
            return self.__bool(**kwargs)
        elif self.__type == DataType.DATE or self.__type == DataType.DATE_ARRAY:
            return self.__date(**kwargs)
        elif self.__type == "ref":
            return self.__ref(**kwargs)
        else:
            raise ValueError(f"Unknown type {self.__type}")

    def __str(
        self,
        count: bool = False,
        top_occurrences_count: bool = False,
        top_occurrences_value: bool = False,
    ) -> _MetricsStr:
        return _MetricsStr(
            property_name=self.__property,
            count=count,
            top_occurrences_count=top_occurrences_count,
            top_occurrences_value=top_occurrences_value,
        )

    def __int(
        self,
        count: bool = False,
        maximum: bool = False,
        mean: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
        sum_: bool = False,
    ) -> _MetricsInt:
        return _MetricsInt(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            mean=mean,
            median=median,
            minimum=minimum,
            mode=mode,
            sum_=sum_,
        )

    def __float(
        self,
        count: bool = False,
        maximum: bool = False,
        mean: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
        sum_: bool = False,
    ) -> _MetricsFloat:
        return _MetricsFloat(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            mean=mean,
            median=median,
            minimum=minimum,
            mode=mode,
            sum_=sum_,
        )

    def __bool(
        self,
        count: bool = False,
        percentage_false: bool = False,
        percentage_true: bool = False,
        total_false: bool = False,
        total_true: bool = False,
    ) -> _MetricsBool:
        return _MetricsBool(
            property_name=self.__property,
            count=count,
            percentage_false=percentage_false,
            percentage_true=percentage_true,
            total_false=total_false,
            total_true=total_true,
        )

    def __date(
        self,
        count: bool = False,
        maximum: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
    ) -> _MetricsDate:
        return _MetricsDate(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            median=median,
            minimum=minimum,
            mode=mode,
        )

    def __ref(
        self,
        pointing_to: bool = False,
    ) -> _MetricsRef:
        return _MetricsRef(
            property_name=self.__property,
            pointing_to=pointing_to,
        )

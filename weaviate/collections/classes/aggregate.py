from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Union,
)
from typing_extensions import TypeVar

from pydantic import BaseModel, Field

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


class _MetricsText(_MetricsBase):
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


class _MetricsNum(_MetricsBase):
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


class _MetricsInteger(_MetricsNum):
    pass


class _MetricsNumber(_MetricsNum):
    pass


class _MetricsBoolean(_MetricsBase):
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


class _MetricsReference(BaseModel):
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
    _MetricsText,
    _MetricsInteger,
    _MetricsNumber,
    _MetricsDate,
    _MetricsBoolean,
    _MetricsReference,
]

PropertiesMetrics = Union[_Metrics, List[_Metrics]]


class Metrics:
    """Define the metrics to be returned based on a property when aggregating over a collection.

    Use the `__init__` method to define the name to the property to be aggregated on.
    Then use the `text`, `integer`, `number`, `boolean`, `date_`, or `reference` methods to define the metrics to be returned.

    See [the docs](https://weaviate.io/developers/weaviate/search/aggregate) for more details!
    """

    def __init__(self, property_: str) -> None:
        self.__property = property_

    def text(
        self,
        count: bool = False,
        top_occurrences_count: bool = False,
        top_occurrences_value: bool = False,
    ) -> _MetricsText:
        """Define the metrics to be returned for a TEXT or TEXT_ARRAY property when aggregating over a collection.

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
        return _MetricsText(
            property_name=self.__property,
            count=count,
            top_occurrences_count=top_occurrences_count,
            top_occurrences_value=top_occurrences_value,
        )

    def integer(
        self,
        count: bool = False,
        maximum: bool = False,
        mean: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
        sum_: bool = False,
    ) -> _MetricsInteger:
        """Define the metrics to be returned for an INT or INT_ARRAY property when aggregating over a collection.

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
            A `_MetricsInteger` object that includes the metrics to be returned.
        """
        return _MetricsInteger(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            mean=mean,
            median=median,
            minimum=minimum,
            mode=mode,
            sum_=sum_,
        )

    def number(
        self,
        count: bool = False,
        maximum: bool = False,
        mean: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
        sum_: bool = False,
    ) -> _MetricsNumber:
        """Define the metrics to be returned for a NUMBER or NUMBER_ARRAY property when aggregating over a collection.

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
            A `_MetricsNumber` object that includes the metrics to be returned.
        """
        return _MetricsNumber(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            mean=mean,
            median=median,
            minimum=minimum,
            mode=mode,
            sum_=sum_,
        )

    def boolean(
        self,
        count: bool = False,
        percentage_false: bool = False,
        percentage_true: bool = False,
        total_false: bool = False,
        total_true: bool = False,
    ) -> _MetricsBoolean:
        """Define the metrics to be returned for a BOOL or BOOL_ARRAY property when aggregating over a collection.

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
            A `_MetricsBoolean` object that includes the metrics to be returned.
        """
        return _MetricsBoolean(
            property_name=self.__property,
            count=count,
            percentage_false=percentage_false,
            percentage_true=percentage_true,
            total_false=total_false,
            total_true=total_true,
        )

    def date_(
        self,
        count: bool = False,
        maximum: bool = False,
        median: bool = False,
        minimum: bool = False,
        mode: bool = False,
    ) -> _MetricsDate:
        """Define the metrics to be returned for a DATE or DATE_ARRAY property when aggregating over a collection.

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
        return _MetricsDate(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            median=median,
            minimum=minimum,
            mode=mode,
        )

    def reference(
        self,
        pointing_to: bool = False,
    ) -> _MetricsReference:
        """Define the metrics to be returned for a cross-reference property when aggregating over a collection.

        Arguments:
            `pointing_to`
                Whether to include the collection names that this property references.

        Returns:
            A `_MetricsReference` object that includes the metrics to be returned.
        """
        return _MetricsReference(
            property_name=self.__property,
            pointing_to=pointing_to,
        )

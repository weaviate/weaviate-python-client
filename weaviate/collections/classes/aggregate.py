from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Union,
)
from typing_extensions import TypeVar

from pydantic import BaseModel, Field

from weaviate.collections.classes.types import _WeaviateInput

N = TypeVar("N", int, float)


@dataclass
class AggregateInteger:
    """The aggregation result for an int property."""

    count: Optional[int]
    maximum: Optional[int]
    mean: Optional[float]
    median: Optional[float]
    minimum: Optional[int]
    mode: Optional[int]
    sum_: Optional[int]


@dataclass
class AggregateNumber:
    """The aggregation result for a number property."""

    count: Optional[int]
    maximum: Optional[float]
    mean: Optional[float]
    median: Optional[float]
    minimum: Optional[float]
    mode: Optional[float]
    sum_: Optional[float]


@dataclass
class TopOccurrence:
    """The top occurrence of a text property."""

    count: Optional[int]
    value: Optional[str]


@dataclass
class AggregateText:
    """The aggregation result for a text property."""

    count: Optional[int]
    top_occurrences: List[TopOccurrence]


@dataclass
class AggregateBoolean:
    """The aggregation result for a boolean property."""

    count: Optional[int]
    percentage_false: Optional[float]
    percentage_true: Optional[float]
    total_false: Optional[int]
    total_true: Optional[int]


# Aggregate references currently bugged on Weaviate's side
# @dataclass
# class AggregateReference:
#     """The aggregation result for a cross-reference property."""

#     pointing_to: Optional[str]


@dataclass
class AggregateDate:
    """The aggregation result for a date property."""

    count: Optional[int]
    maximum: Optional[str]
    median: Optional[str]
    minimum: Optional[str]
    mode: Optional[str]


AggregateResult = Union[
    AggregateInteger,
    AggregateNumber,
    AggregateText,
    AggregateBoolean,
    AggregateDate,
    # AggregateReference, # Aggregate references currently bugged on Weaviate's side
]

AProperties = Dict[str, AggregateResult]


@dataclass
class AggregateReturn:
    """The aggregation result for a collection."""

    properties: AProperties
    total_count: Optional[int]


@dataclass
class GroupedBy:
    """The property that the collection was grouped by."""

    prop: str
    value: str


@dataclass
class AggregateGroup:
    """The aggregation result for a collection grouped by a property."""

    grouped_by: GroupedBy
    properties: AProperties
    total_count: Optional[int]


@dataclass
class AggregateGroupByReturn:
    """The aggregation results for a collection grouped by a property."""

    groups: List[AggregateGroup]


class _MetricsBase(BaseModel):
    property_name: str
    count: bool


class _MetricsText(_MetricsBase):
    top_occurrences_count: bool
    top_occurrences_value: bool
    min_occurrences: Optional[int]

    def to_gql(self) -> str:
        limit = f"(limit: {self.min_occurrences})" if self.min_occurrences is not None else ""
        body = " ".join(
            [
                "count" if self.count else "",
                (
                    "topOccurrences" + limit + " {"
                    if self.top_occurrences_count or self.top_occurrences_value
                    else ""
                ),
                "occurs" if self.top_occurrences_count else "",
                "value" if self.top_occurrences_value else "",
                "}" if self.top_occurrences_count or self.top_occurrences_value else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


class _MetricsNum(_MetricsBase):
    maximum: bool
    mean: bool
    median: bool
    minimum: bool
    mode: bool
    sum_: bool

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
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
    percentage_false: bool
    percentage_true: bool
    total_false: bool
    total_true: bool

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
                "percentageFalse" if self.percentage_false else "",
                "percentageTrue" if self.percentage_true else "",
                "totalFalse" if self.total_false else "",
                "totalTrue" if self.total_true else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


class _MetricsDate(_MetricsBase):
    maximum: bool
    median: bool
    minimum: bool
    mode: bool

    def to_gql(self) -> str:
        body = " ".join(
            [
                "count" if self.count else "",
                "maximum" if self.maximum else "",
                "median" if self.median else "",
                "minimum" if self.minimum else "",
                "mode" if self.mode else "",
            ]
        )
        return f"{self.property_name} {{ {body} }}"


# Aggregate references currently bugged on Weaviate's side
# class _MetricsReference(BaseModel):
#     property_name: str
#     pointing_to: bool

#     def to_gql(self) -> str:
#         body = " ".join(
#             [
#                 "pointingTo" if self.pointing_to else "",
#             ]
#         )
#         return f"{self.property_name} {{ {body} }}"


_Metrics = Union[
    _MetricsText,
    _MetricsInteger,
    _MetricsNumber,
    _MetricsDate,
    _MetricsBoolean,
    # _MetricsReference, # Aggregate references currently bugged on Weaviate's side
]

PropertiesMetrics = Union[_Metrics, List[_Metrics]]


class GroupByAggregate(_WeaviateInput):
    """Define how the aggregations's group-by operation should be performed."""

    prop: str
    limit: Optional[int] = Field(default=None)


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
        min_occurrences: Optional[int] = None,
    ) -> _MetricsText:
        """Define the metrics to be returned for a TEXT or TEXT_ARRAY property when aggregating over a collection.

        If none of the arguments are provided then all metrics will be returned.

        Arguments:
            `count`
                Whether to include the number of objects that contain this property.
            `top_occurrences_count`
                Whether to include the number of the top occurrences of a property's value.
            `top_occurrences_value`
                Whether to include the value of the top occurrences of a property's value.
            `min_occurrences`
                Only include entries with more occurrences than the given limit.

        Returns:
            A `_MetricsStr` object that includes the metrics to be returned.
        """
        if not any([count, top_occurrences_count, top_occurrences_value]):
            count = True
            top_occurrences_count = True
            top_occurrences_value = True
        return _MetricsText(
            property_name=self.__property,
            count=count,
            top_occurrences_count=top_occurrences_count,
            top_occurrences_value=top_occurrences_value,
            min_occurrences=min_occurrences,
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

        If none of the arguments are provided then all metrics will be returned.

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
        if not any([count, maximum, mean, median, minimum, mode, sum_]):
            count = True
            maximum = True
            mean = True
            median = True
            minimum = True
            mode = True
            sum_ = True
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

        If none of the arguments are provided then all metrics will be returned.

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
        if not any([count, maximum, mean, median, minimum, mode, sum_]):
            count = True
            maximum = True
            mean = True
            median = True
            minimum = True
            mode = True
            sum_ = True
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

        If none of the arguments are provided then all metrics will be returned.

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
        if not any([count, percentage_false, percentage_true, total_false, total_true]):
            count = True
            percentage_false = True
            percentage_true = True
            total_false = True
            total_true = True
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

        If none of the arguments are provided then all metrics will be returned.

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
        if not any([count, maximum, median, minimum, mode]):
            count = True
            maximum = True
            median = True
            minimum = True
            mode = True
        return _MetricsDate(
            property_name=self.__property,
            count=count,
            maximum=maximum,
            median=median,
            minimum=minimum,
            mode=mode,
        )

    # Aggregate references currently bugged on Weaviate's side
    # def reference(
    #     self,
    #     pointing_to: bool = False,
    # ) -> _MetricsReference:
    #     """Define the metrics to be returned for a cross-reference property when aggregating over a collection.

    #     If none of the arguments are provided then all metrics will be returned.

    #     Arguments:
    #         `pointing_to`
    #             Whether to include the collection names that this property references.

    #     Returns:
    #         A `_MetricsReference` object that includes the metrics to be returned.
    #     """
    #     if not any([pointing_to]):
    #         pointing_to = True
    #     return _MetricsReference(
    #         property_name=self.__property,
    #         pointing_to=pointing_to,
    #     )

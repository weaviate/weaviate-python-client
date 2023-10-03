from dataclasses import dataclass
from typing import Dict, Generic, Mapping, Optional, Union
from typing_extensions import TypeAlias, TypeVar

N = TypeVar("N", int, float)


@dataclass
class _AggregateResultsNumber(Generic[N]):
    count: Optional[int]
    maximum: Optional[N]
    mean: Optional[float]
    median: Optional[N]
    mode: Optional[N]
    sum_: Optional[N]
    type_: Optional[str]


_AggregateResultsInt: TypeAlias = _AggregateResultsNumber[int]
_AggregateResultsFloat: TypeAlias = _AggregateResultsNumber[float]


@dataclass
class _TopOccurences:
    occurs: Optional[int]
    value: Optional[str]


@dataclass
class _AggregateResultsStr:
    count: Optional[int]
    top_occurences: Optional[_TopOccurences]
    type_: Optional[str]


@dataclass
class _AggregateResultsBool:
    count: Optional[int]
    percentage_false: Optional[float]
    percentage_true: Optional[float]
    total_false: Optional[int]
    total_true: Optional[int]
    type_: Optional[str]


@dataclass
class _AggregateResultsRef:
    pointing_to: str
    type_: str


AggregateResults: TypeAlias = Union[
    _AggregateResultsInt,
    _AggregateResultsFloat,
    _AggregateResultsStr,
    _AggregateResultsBool,
    _AggregateResultsRef,
]

AggregateProperties = TypeVar(
    "AggregateProperties", bound=Mapping[str, AggregateResults], default=Dict[str, AggregateResults]
)


@dataclass
class _AggregateReturn(Generic[AggregateProperties]):
    properties: AggregateProperties

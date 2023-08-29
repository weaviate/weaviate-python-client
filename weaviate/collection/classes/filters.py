from datetime import datetime
from dataclasses import dataclass
from typing import List, Union

from weaviate_grpc import weaviate_pb2


class _Filters:
    def __and__(self, other: "_Filters"):
        return _FilterAnd(self, other)

    def __or__(self, other: "_Filters"):
        return _FilterOr(self, other)


class _FilterAnd(_Filters):
    def __init__(self, *args: _Filters):
        self.filters: List[_Filters] = list(args)

    # replace with the following once 3.11 is the minimum version
    #     Operator: weaviate_pb2.Filters.OperatorType = weaviate_pb2.Filters.OperatorAnd
    @property
    def operator(self) -> weaviate_pb2.Filters.Operator:
        return weaviate_pb2.Filters.OPERATOR_AND


class _FilterOr(_Filters):
    def __init__(self, *args: _Filters):
        self.filters: List[_Filters] = list(args)

    # replace with the following once 3.11 is the minimum version
    #     Operator: weaviate_pb2.Filters.OperatorType = weaviate_pb2.Filters.OperatorOr
    @property
    def operator(self) -> weaviate_pb2.Filters.Operator:
        return weaviate_pb2.Filters.OPERATOR_OR


FilterValuesList = Union[List[str], List[bool], List[int], List[float], List[datetime.date]]
FilterValues = Union[int, float, str, bool, datetime.date, None, FilterValuesList]


@dataclass
class _FilterValue(_Filters):
    path: Union[str, List[str]]
    value: FilterValues
    operator: weaviate_pb2.Filters.Operator

    def __and__(self, other: "_Filters"):
        return _FilterAnd(self, other)

    def __or__(self, other: "_Filters"):
        return _FilterOr(self, other)


@dataclass
class Filter:
    path: Union[str, List[str]]
    length: bool = False

    def __post_init__(self):
        if isinstance(self.path, str):
            path = [self.path]
        else:
            path = self.path

        if self.length:
            self.__internal_path = "len(" + path[-1] + ")"
        else:
            self.__internal_path = path

    def is_none(self, val: bool) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path, value=val, operator=weaviate_pb2.Filters.OPERATOR_IS_NULL
        )

    def contains_any(self, val: FilterValuesList) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=weaviate_pb2.Filters.OPERATOR_CONTAINS_ANY,
        )

    def contains_all(self, val: FilterValuesList) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=weaviate_pb2.Filters.OPERATOR_CONTAINS_ALL,
        )

    def equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path, value=val, operator=weaviate_pb2.Filters.OPERATOR_EQUAL
        )

    def not_equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path, value=val, operator=weaviate_pb2.Filters.OPERATOR_NOT_EQUAL
        )

    def less_than(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path, value=val, operator=weaviate_pb2.Filters.OPERATOR_LESS_THAN
        )

    def less_than_equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=weaviate_pb2.Filters.OPERATOR_LESS_THAN_EQUAL,
        )

    def greater_than(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=weaviate_pb2.Filters.OPERATOR_GREATER_THAN,
        )

    def greater_than_equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=weaviate_pb2.Filters.OPERATOR_GREATER_THAN_EQUAL,
        )

    def like(self, val: str) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path, value=val, operator=weaviate_pb2.Filters.OPERATOR_LIKE
        )

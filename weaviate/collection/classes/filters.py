from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Union

from weaviate.weaviate_types import UUID
from weaviate_grpc import weaviate_pb2


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
    AND = "And"
    OR = "Or"

    def _to_grpc(self) -> weaviate_pb2.Filters.Operator:
        if self == _Operator.EQUAL:
            return weaviate_pb2.Filters.OPERATOR_EQUAL
        elif self == _Operator.NOT_EQUAL:
            return weaviate_pb2.Filters.OPERATOR_NOT_EQUAL
        elif self == _Operator.LESS_THAN:
            return weaviate_pb2.Filters.OPERATOR_LESS_THAN
        elif self == _Operator.LESS_THAN_EQUAL:
            return weaviate_pb2.Filters.OPERATOR_LESS_THAN_EQUAL
        elif self == _Operator.GREATER_THAN:
            return weaviate_pb2.Filters.OPERATOR_GREATER_THAN
        elif self == _Operator.GREATER_THAN_EQUAL:
            return weaviate_pb2.Filters.OPERATOR_GREATER_THAN_EQUAL
        elif self == _Operator.LIKE:
            return weaviate_pb2.Filters.OPERATOR_LIKE
        elif self == _Operator.IS_NULL:
            return weaviate_pb2.Filters.OPERATOR_IS_NULL
        elif self == _Operator.CONTAINS_ANY:
            return weaviate_pb2.Filters.OPERATOR_CONTAINS_ANY
        elif self == _Operator.CONTAINS_ALL:
            return weaviate_pb2.Filters.OPERATOR_CONTAINS_ALL
        elif self == _Operator.AND:
            return weaviate_pb2.Filters.OPERATOR_AND
        elif self == _Operator.OR:
            return weaviate_pb2.Filters.OPERATOR_OR
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


FilterValuesList = Union[List[str], List[bool], List[int], List[float], List[datetime], List[UUID]]
FilterValues = Union[int, float, str, bool, datetime, UUID, None, FilterValuesList]


@dataclass
class _FilterValue(_Filters):
    path: Union[str, List[str]]
    value: FilterValues
    operator: _Operator


class Filter:
    def __init__(self, path: Union[str, List[str]], length: bool = False):
        if isinstance(path, str):
            path = [path]
        if length:
            path[-1] = "len(" + path[-1] + ")"
        self.__internal_path = path

    def is_none(self, val: bool) -> _FilterValue:
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.IS_NULL)

    def contains_any(self, val: FilterValuesList) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.CONTAINS_ANY,
        )

    def contains_all(self, val: FilterValuesList) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.CONTAINS_ALL,
        )

    def equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.EQUAL)

    def not_equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.NOT_EQUAL)

    def less_than(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.LESS_THAN)

    def less_than_equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.LESS_THAN_EQUAL,
        )

    def greater_than(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.GREATER_THAN,
        )

    def greater_than_equal(self, val: FilterValues) -> _FilterValue:
        return _FilterValue(
            path=self.__internal_path,
            value=val,
            operator=_Operator.GREATER_THAN_EQUAL,
        )

    def like(self, val: str) -> _FilterValue:
        return _FilterValue(path=self.__internal_path, value=val, operator=_Operator.LIKE)

import datetime

import pytest

import weaviate
import weaviate.classes as wvc
from weaviate.collections.classes.filters import (
    Filter,
    _FilterAnd,
    _FilterNot,
    _FilterOr,
    _Operator,
)
from weaviate.proto.v1 import base_pb2


def test_empty_input_contains_any() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_id().contains_any([])
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").contains_any([])


def test_empty_input_contains_all() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").contains_all([])


def test_filter_lists() -> None:
    f1 = wvc.query.Filter.by_property("test").equal("test")
    f2 = wvc.query.Filter.by_creation_time().greater_or_equal(datetime.datetime.now())

    and_list = wvc.query.Filter.all_of([f1, f2])
    and_direct = f1 & f2
    assert isinstance(and_list, _FilterAnd)
    assert isinstance(and_direct, _FilterAnd)
    assert and_list.filters == and_direct.filters

    or_list = wvc.query.Filter.any_of([f1, f2])
    or_direct = f1 | f2
    assert isinstance(or_list, _FilterOr)
    assert isinstance(or_direct, _FilterOr)
    assert or_list.filters == or_direct.filters


def test_filter_lists_one_entry() -> None:
    f1 = wvc.query.Filter.by_property("test").equal("test")

    and_list = wvc.query.Filter.all_of([f1])
    assert and_list == f1

    or_list = wvc.query.Filter.any_of([f1])
    assert or_list == f1


def test_filter_lists_empty() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.all_of([])

    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.any_of([])


def test_filter_bitwise_and_assignment() -> None:
    f1 = wvc.query.Filter.by_property("test").equal("test")
    f2 = wvc.query.Filter.by_creation_time().greater_or_equal(datetime.datetime.now())
    f3 = wvc.query.Filter.by_update_time().less_or_equal(datetime.datetime.now())

    f4 = f1 & f2
    f4 &= f3
    and_direct = wvc.query.Filter.all_of([f1, f2]) & f3
    assert isinstance(f4, _FilterAnd)
    assert isinstance(and_direct, _FilterAnd)

    assert isinstance(f4.filters[0], _FilterAnd)
    assert isinstance(and_direct.filters[0], _FilterAnd)
    assert f4.filters[0].filters == and_direct.filters[0].filters
    assert f4.filters[1] == f3


def test_filter_bitwise_or_assignment() -> None:
    f1 = wvc.query.Filter.by_property("test").equal("test")
    f2 = wvc.query.Filter.by_creation_time().greater_or_equal(datetime.datetime.now())
    f3 = wvc.query.Filter.by_update_time().less_or_equal(datetime.datetime.now())

    f4 = f1 | f2
    f4 |= f3
    or_direct = wvc.query.Filter.any_of([f1, f2]) | f3
    assert isinstance(f4, _FilterOr)
    assert isinstance(or_direct, _FilterOr)

    assert isinstance(f4.filters[0], _FilterOr)
    assert isinstance(or_direct.filters[0], _FilterOr)
    assert f4.filters[0].filters == or_direct.filters[0].filters
    assert f4.filters[1] == f3


def test_filter_bitwise_invert_assignment() -> None:
    f1 = wvc.query.Filter.by_property("test").equal("test")
    not_f1 = wvc.query.Filter.not_(f1)

    invert_f1 = ~f1

    assert isinstance(invert_f1, _FilterNot)
    assert isinstance(not_f1, _FilterNot)
    assert len(invert_f1.filters) == 1
    assert invert_f1.filters == not_f1.filters


def test_auto_capitalize_first_letter_by_ref_multi_target() -> None:
    result = Filter.by_ref_multi_target(link_on="ref1", target_collection="test")
    target_collection_stored = result._FilterByRef__target.target_collection
    assert target_collection_stored == "Test"


@pytest.mark.parametrize(
    "operator,want",
    [
        (_Operator.EQUAL, base_pb2.Filters.OPERATOR_EQUAL),
        (_Operator.NOT_EQUAL, base_pb2.Filters.OPERATOR_NOT_EQUAL),
        (_Operator.LESS_THAN, base_pb2.Filters.OPERATOR_LESS_THAN),
        (_Operator.LESS_THAN_EQUAL, base_pb2.Filters.OPERATOR_LESS_THAN_EQUAL),
        (_Operator.GREATER_THAN, base_pb2.Filters.OPERATOR_GREATER_THAN),
        (_Operator.GREATER_THAN_EQUAL, base_pb2.Filters.OPERATOR_GREATER_THAN_EQUAL),
        (_Operator.LIKE, base_pb2.Filters.OPERATOR_LIKE),
        (_Operator.IS_NULL, base_pb2.Filters.OPERATOR_IS_NULL),
        (_Operator.CONTAINS_ANY, base_pb2.Filters.OPERATOR_CONTAINS_ANY),
        (_Operator.CONTAINS_ALL, base_pb2.Filters.OPERATOR_CONTAINS_ALL),
        (_Operator.CONTAINS_NONE, base_pb2.Filters.OPERATOR_CONTAINS_NONE),
        (_Operator.WITHIN_GEO_RANGE, base_pb2.Filters.OPERATOR_WITHIN_GEO_RANGE),
        (_Operator.AND, base_pb2.Filters.OPERATOR_AND),
        (_Operator.OR, base_pb2.Filters.OPERATOR_OR),
        (_Operator.NOT, base_pb2.Filters.OPERATOR_NOT),
    ],
)
def test_operator_to_grpc(operator: _Operator, want: base_pb2.Filters.Operator) -> None:
    assert operator._to_grpc() == want, "wrong pb operator"

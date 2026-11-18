import datetime
import uuid
from typing import Any, List

import pytest

import weaviate
import weaviate.classes as wvc
from weaviate.collections.classes.filters import (
    Filter,
    _FilterAnd,
    _FilterNot,
    _FilterOr,
    _FilterValue,
    _Operator,
)
from weaviate.collections.filters import _FilterToGRPC, _FilterToREST
from weaviate.proto.v1 import base_pb2


def test_empty_input_contains_any() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_id().contains_any([])
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").contains_any([])
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_creation_time().contains_any([])
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_update_time().contains_any([])


def test_empty_input_contains_none_time() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_creation_time().contains_none([])
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_update_time().contains_none([])


def test_empty_input_contains_all() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").contains_all([])


def test_empty_list_equal() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").equal([])


def test_empty_list_not_equal() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").not_equal([])


def test_empty_list_less_than() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").less_than([])


def test_empty_list_less_or_equal() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").less_or_equal([])


def test_empty_list_greater_than() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").greater_than([])


def test_empty_list_greater_or_equal() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").greater_or_equal([])


def test_empty_list_grpc_conversion() -> None:
    """Ensure the gRPC converter raises WeaviateInvalidInputError for empty lists."""
    fv = _FilterValue(target="test", value=[], operator=_Operator.EQUAL)
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        _FilterToGRPC.convert(fv)


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


def test_reuse_by_ref_builder_for_independent_filters() -> None:
    ref = Filter.by_ref("hasCategory")

    name_filter = ref.by_property("name").equal("Electronics")
    rating_filter = ref.by_property("rating").greater_than(4)

    assert name_filter.target.link_on == "hasCategory"
    assert name_filter.target.target == "name"
    assert rating_filter.target.link_on == "hasCategory"
    assert rating_filter.target.target == "rating"
    assert name_filter.target is not rating_filter.target

    property_filter = ref.by_property("name")
    first_value = property_filter.equal("Electronics")
    second_value = property_filter.equal("Appliances")

    assert first_value.target.link_on == "hasCategory"
    assert first_value.target.target == "name"
    assert second_value.target.link_on == "hasCategory"
    assert second_value.target.target == "name"
    assert first_value.target is not second_value.target


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


# (values, gRPC array field, REST array key) for each supported filter value type
SEQUENCE_FILTER_VALUES = [
    (["a", "b"], "value_text_array", "valueTextArray"),
    ([1, 2], "value_int_array", "valueIntArray"),
    ([1.5, 2.5], "value_number_array", "valueNumberArray"),
    ([True, False], "value_boolean_array", "valueBooleanArray"),
    ([uuid.UUID(int=1), uuid.UUID(int=2)], "value_text_array", "valueTextArray"),
    (
        [
            datetime.datetime(2023, 1, 1, tzinfo=datetime.timezone.utc),
            datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        ],
        "value_text_array",
        "valueDateArray",
    ),
]
SEQUENCE_FILTER_IDS = ["text", "int", "float", "bool", "uuid", "date"]


@pytest.mark.parametrize("method", ["contains_any", "contains_all", "contains_none"])
@pytest.mark.parametrize(
    "values,grpc_field,_rest_key", SEQUENCE_FILTER_VALUES, ids=SEQUENCE_FILTER_IDS
)
def test_sequence_filter_values_to_grpc(
    method: str, values: List[Any], grpc_field: str, _rest_key: str
) -> None:
    from_list = getattr(wvc.query.Filter.by_property("test"), method)(values)
    from_tuple = getattr(wvc.query.Filter.by_property("test"), method)(tuple(values))

    as_list = _FilterToGRPC.convert(from_list)
    as_tuple = _FilterToGRPC.convert(from_tuple)

    assert as_list.HasField(grpc_field), "the list form must send the values"
    assert as_tuple == as_list, "a tuple must serialise like the equivalent list"


@pytest.mark.parametrize("method", ["contains_any", "contains_all", "contains_none"])
@pytest.mark.parametrize(
    "values,_grpc_field,rest_key", SEQUENCE_FILTER_VALUES, ids=SEQUENCE_FILTER_IDS
)
def test_sequence_filter_values_to_rest(
    method: str, values: List[Any], _grpc_field: str, rest_key: str
) -> None:
    from_list = getattr(wvc.query.Filter.by_property("test"), method)(values)
    from_tuple = getattr(wvc.query.Filter.by_property("test"), method)(tuple(values))

    as_list = _FilterToREST.convert(from_list)

    assert rest_key in as_list, "the list form must send the values"
    assert _FilterToREST.convert(from_tuple) == as_list, (
        "a tuple must serialise like the equivalent list"
    )


@pytest.mark.parametrize("value", ["test", ""])
def test_string_filter_values_are_not_sequences(value: str) -> None:
    filter_ = wvc.query.Filter.by_property("test").equal(value)

    assert _FilterToGRPC.convert(filter_).value_text == value
    assert _FilterToREST.convert(filter_) == {
        "operator": "Equal",
        "path": ["test"],
        "valueText": value,
    }


def test_empty_tuple_grpc_conversion() -> None:
    """Ensure the gRPC converter treats an empty tuple like an empty list."""
    fv = _FilterValue(target="test", value=(), operator=_Operator.EQUAL)
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        _FilterToGRPC.convert(fv)


def test_empty_tuple_rest_conversion() -> None:
    """Ensure the REST converter treats an empty tuple like an empty list."""
    fv = _FilterValue(target="test", value=(), operator=_Operator.EQUAL)
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        _FilterToREST.convert(fv)


@pytest.mark.parametrize("method", ["contains_any", "contains_all", "contains_none"])
def test_empty_tuple_input(method: str) -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        getattr(wvc.query.Filter.by_property("test"), method)(())

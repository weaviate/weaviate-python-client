import datetime

import pytest

import weaviate
import weaviate.classes as wvc
from weaviate.collections.classes.filters import _FilterAnd, _FilterOr


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
    assert and_list.filters == and_direct.filters

    or_list = wvc.query.Filter.any_of([f1, f2])
    or_direct = f1 | f2
    assert isinstance(or_list, _FilterOr)
    assert or_list.filters == or_direct.filters

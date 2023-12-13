import pytest

from dataclasses import dataclass

from pydantic import ValidationError

from weaviate.collections.classes.filters import Filter, _Operator


@dataclass
class Bad:
    thing: str


def test_bad_input() -> None:
    with pytest.raises(ValidationError):
        Filter("name").equal(val=Bad("thing"))


def test_good_input() -> None:
    filter_ = Filter("name").equal(val="thing")
    assert filter_.operator == _Operator.EQUAL
    assert filter_.path == ["name"]
    assert filter_.value == "thing"

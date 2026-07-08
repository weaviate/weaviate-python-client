from weaviate.str_enum import BaseEnum


class _Color(BaseEnum):
    RED = "red"
    GREEN = "green"


def test_member_name_string_is_contained():
    # `in` matches by member *name*, so the uppercase name is found.
    assert "RED" in _Color
    assert "GREEN" in _Color


def test_unknown_string_is_not_contained():
    assert "PURPLE" not in _Color


def test_member_value_string_is_not_a_membership_match():
    # The lowercase *value* is not a member name, so it is not contained.
    assert "red" not in _Color


def test_enum_member_is_contained():
    assert _Color.RED in _Color


def test_non_string_non_member_is_not_contained():
    # A non-string that lacks a ``.name`` falls back to the string check
    # and is therefore not contained.
    assert 12345 not in _Color

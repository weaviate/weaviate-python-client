import warnings

import pytest

from weaviate.warnings import _Warnings


def _capture(func, *args):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        func(*args)
    assert len(caught) == 1
    return caught[0]


def test_auth_with_anon_weaviate_emits_user_warning():
    record = _capture(_Warnings.auth_with_anon_weaviate)
    assert issubclass(record.category, UserWarning)
    assert "Auth001" in str(record.message)


def test_auth_negative_expiration_time_includes_value():
    record = _capture(_Warnings.auth_negative_expiration_time, 30)
    assert issubclass(record.category, UserWarning)
    assert "Auth003" in str(record.message)
    assert "30" in str(record.message)


def test_auth_no_refresh_token_without_length():
    record = _capture(_Warnings.auth_no_refresh_token)
    assert "Auth002" in str(record.message)
    assert "no expiration time" in str(record.message)


def test_auth_no_refresh_token_with_length():
    record = _capture(_Warnings.auth_no_refresh_token, 60)
    assert "Auth002" in str(record.message)
    assert "only valid for 60s" in str(record.message)


@pytest.mark.parametrize(
    "func, args, code",
    [
        (_Warnings.sharding_actual_count_is_deprecated, ("actualCount",), "Dep018"),
        (_Warnings.deprecated_tenant_type, ("HOT", "ACTIVE"), "Dep021"),
    ],
)
def test_deprecation_warnings(func, args, code):
    record = _capture(func, *args)
    assert issubclass(record.category, DeprecationWarning)
    assert code in str(record.message)

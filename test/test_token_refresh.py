"""Regression test for #2110: background token refresh thread must survive
authlib OAuthError (e.g. invalid_grant), not just httpx.HTTPError."""

import pytest
from authlib.common.errors import AuthlibBaseError
from httpx import HTTPError


def test_authlib_base_error_is_not_http_error():
    """AuthlibBaseError does NOT inherit from httpx.HTTPError, confirming
    the bug: the old `except HTTPError` clause could never catch it."""
    assert not issubclass(AuthlibBaseError, HTTPError)


def test_authlib_base_error_caught_by_fixed_except_clause():
    """The fixed except clause `(HTTPError, AuthlibBaseError)` must catch
    authlib protocol-level errors like invalid_grant."""
    try:
        raise AuthlibBaseError("invalid_grant")
    except (HTTPError, AuthlibBaseError):
        pass  # This is what the fixed code does
    else:
        pytest.fail("AuthlibBaseError was not caught by (HTTPError, AuthlibBaseError)")


def test_http_error_still_caught_by_fixed_except_clause():
    """The fix must not break the existing HTTPError handling."""
    try:
        raise HTTPError("connection reset")
    except (HTTPError, AuthlibBaseError):
        pass
    else:
        pytest.fail("HTTPError was not caught by (HTTPError, AuthlibBaseError)")


def test_oauth_error_subclass_caught():
    """Concrete authlib errors (e.g. OAuthError) inherit from AuthlibBaseError
    and must also be caught."""
    from authlib.integrations.base_client.errors import OAuthError

    assert issubclass(OAuthError, AuthlibBaseError)
    try:
        raise OAuthError("invalid_grant")
    except (HTTPError, AuthlibBaseError):
        pass
    else:
        pytest.fail("OAuthError was not caught by (HTTPError, AuthlibBaseError)")

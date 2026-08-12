"""Tests for background token refresh error classification."""

import pytest
from authlib.integrations.base_client.errors import OAuthError
from httpx import HTTPError

from weaviate.connect.v4 import _is_retryable_token_refresh_error


def test_token_refresh_retries_transport_errors() -> None:
    assert _is_retryable_token_refresh_error(HTTPError("connection reset"))


@pytest.mark.parametrize("error", ["server_error", "temporarily_unavailable"])
def test_token_refresh_retries_transient_oauth_errors(error: str) -> None:
    assert _is_retryable_token_refresh_error(OAuthError(error=error))


@pytest.mark.parametrize("error", ["invalid_grant", "invalid_client", "access_denied"])
def test_token_refresh_stops_on_permanent_oauth_errors(error: str) -> None:
    assert not _is_retryable_token_refresh_error(OAuthError(error=error))

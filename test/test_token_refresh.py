"""Tests for the background OIDC token-refresh thread in `weaviate.connect.v4`.

These run without a Weaviate instance and without an identity provider: the
`OAuth2Client` is real but its network-facing methods are replaced.
"""

import time
from typing import Any, Dict, List, Optional

import pytest
from authlib.integrations.base_client import OAuthError
from authlib.integrations.httpx_client import OAuth2Client
from httpx import HTTPError

from weaviate.connect.v4 import ConnectionSync
from weaviate.warnings import _Warnings

TOKEN_ENDPOINT = "https://localhost/token"


def test_oauth_error_is_not_an_http_error() -> None:
    """Guards the reason the dedicated `except OAuthError` branch has to exist."""
    assert not issubclass(OAuthError, HTTPError)


class _FakeSession:
    """Stands in for the authlib session returned by `_Auth.get_auth_session()`."""

    def __init__(self, token: Dict[str, Any]) -> None:
        self.__token = token

    def fetch_token(self) -> Dict[str, Any]:
        return self.__token


class _FakeAuth:
    """Minimal duck-typed stand-in for `_Auth`, which only needs these two methods."""

    def __init__(self, token: Dict[str, Any]) -> None:
        self.__token = token
        self.calls = 0

    def get_auth_session(self) -> "_FakeSession":
        return _FakeSession(self.__token)

    def result(self, session: "_FakeSession") -> "_FakeSession":
        self.calls += 1
        return session


def _make_client(token: Dict[str, Any]) -> OAuth2Client:
    client = OAuth2Client(client_id="test-client", token=token)
    client.metadata["token_endpoint"] = TOKEN_ENDPOINT
    return client


def _make_connection(client: OAuth2Client) -> ConnectionSync:
    """Build a connection with only the attributes the refresh helper touches.

    `_shutdown_background_event` is deliberately left unset: it is assigned by
    `_create_background_token_refresh` itself before the thread reads it.
    """
    connection = object.__new__(ConnectionSync)
    connection._client = client
    return connection


@pytest.fixture
def recorded_warnings(monkeypatch: pytest.MonkeyPatch) -> List[Exception]:
    recorded: List[Exception] = []
    monkeypatch.setattr(
        _Warnings, "token_refresh_failed", staticmethod(lambda exc: recorded.append(exc))
    )
    return recorded


def _run_refresh(
    connection: ConnectionSync, auth: Optional[_FakeAuth], seconds: float = 3.0
) -> None:
    """Start the background refresh and let it complete at least one cycle."""
    connection._create_background_token_refresh(auth)  # type: ignore[arg-type]
    try:
        time.sleep(seconds)
    finally:
        assert connection._shutdown_background_event is not None
        connection._shutdown_background_event.set()


def _refresh_thread_is_alive() -> bool:
    import threading

    return any(
        thread.name == "TokenRefresh" and thread.is_alive() for thread in threading.enumerate()
    )


def test_oauth_error_does_not_kill_the_refresh_thread(
    recorded_warnings: List[Exception],
) -> None:
    """An `invalid_grant` from the IdP must be reported, not silently end all refreshes."""
    client = _make_client({"access_token": "old", "refresh_token": "stale", "expires_in": 1})

    def _reject(**kwargs: Any) -> Dict[str, Any]:
        raise OAuthError(error="invalid_grant", description="Refresh token is invalid")

    client.refresh_token = _reject  # type: ignore[method-assign]

    auth = _FakeAuth({"access_token": "fresh", "refresh_token": "fresh-refresh", "expires_in": 60})
    connection = _make_connection(client)

    _run_refresh(connection, auth)

    assert recorded_warnings, "the OAuth2 rejection was swallowed instead of warned about"
    assert isinstance(recorded_warnings[0], OAuthError)
    # Re-authenticated from scratch rather than retrying the rejected refresh token.
    assert auth.calls >= 1
    assert client.token["access_token"] == "fresh"
    assert _refresh_thread_is_alive()


def test_oauth_error_without_credentials_still_keeps_the_thread_alive(
    recorded_warnings: List[Exception],
) -> None:
    """With no `_Auth` to fall back on, the loop must warn and keep running."""
    client = _make_client({"access_token": "old", "refresh_token": "stale", "expires_in": 1})

    def _reject(**kwargs: Any) -> Dict[str, Any]:
        raise OAuthError(error="invalid_grant", description="Refresh token is invalid")

    client.refresh_token = _reject  # type: ignore[method-assign]
    connection = _make_connection(client)

    _run_refresh(connection, None)

    assert recorded_warnings, "the OAuth2 rejection was swallowed instead of warned about"
    assert all(isinstance(exc, OAuthError) for exc in recorded_warnings)
    assert _refresh_thread_is_alive()


def test_http_error_still_retries(recorded_warnings: List[Exception]) -> None:
    """The pre-existing `HTTPError` behaviour is unchanged."""
    client = _make_client({"access_token": "old", "refresh_token": "stale", "expires_in": 1})

    def _fail(**kwargs: Any) -> Dict[str, Any]:
        raise HTTPError("connection reset")

    client.refresh_token = _fail  # type: ignore[method-assign]

    auth = _FakeAuth({"access_token": "fresh", "expires_in": 60})
    connection = _make_connection(client)

    _run_refresh(connection, auth)

    assert recorded_warnings
    assert all(isinstance(exc, HTTPError) for exc in recorded_warnings)
    # An HTTPError must not trigger the re-authentication path.
    assert auth.calls == 0
    assert client.token["access_token"] == "old"
    assert _refresh_thread_is_alive()


def test_successful_refresh_does_not_warn(recorded_warnings: List[Exception]) -> None:
    """Sanity check that the happy path is untouched."""
    client = _make_client({"access_token": "old", "refresh_token": "good", "expires_in": 1})

    def _succeed(**kwargs: Any) -> Dict[str, Any]:
        return {"access_token": "new", "refresh_token": "good", "expires_in": 60}

    client.refresh_token = _succeed  # type: ignore[method-assign]
    connection = _make_connection(client)

    _run_refresh(connection, None)

    assert recorded_warnings == []
    assert client.token["access_token"] == "new"

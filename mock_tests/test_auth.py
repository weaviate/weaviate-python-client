import asyncio
import json
import threading
import time
import warnings
from typing import List, Union

import grpc
import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import CLIENT_ID, MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.connect.v4 import _ConnectionBase
from weaviate.exceptions import MissingScopeException, UnexpectedStatusCodeError

ACCESS_TOKEN = "HELLO!IamAnAccessToken"
CLIENT_SECRET = "SomeSecret.DontTell"
SCOPE = "IcanBeAnything"
REFRESH_TOKEN = "UseMeToRefreshYourAccessToken"


def test_user_password(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    """Test that client sends username and pw with the correct body to the token endpoint and uses the correct token."""
    user = "AUsername"
    pw = "SomePassWord"

    # note: order matters. If this handler is not called, check of the order of arguments changed
    weaviate_auth_mock.expect_request(
        "/auth",
        data=f"grant_type=password&username={user}&password={pw}&client_id={CLIENT_ID}",
    ).respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthClientPassword(user, pw),
    ) as client:
        client.collections.list_all()  # some call that includes authorization
    weaviate_auth_mock.check_assertions()


def test_bearer_token(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    """Test that client sends the given bearer token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(ACCESS_TOKEN, refresh_token=REFRESH_TOKEN),
    ) as client:
        client.collections.list_all()  # some call that includes authorization

    weaviate_auth_mock.check_assertions()


def test_client_credentials(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server):
    """Test that client sends the client credentials to the token endpoint and uses the correct token."""
    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500}
    )
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthClientCredentials(
            client_secret=CLIENT_SECRET, scope=SCOPE
        ),
    ) as client:
        client.collections.list_all()  # some call that includes authorization

    weaviate_auth_mock.check_assertions()


@pytest.mark.asyncio
async def test_client_credentials_refresh_async(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """Test the refresh_session branch of the async token refresher.

    Client-credentials tokens carry no refresh token, so the refresher must get a whole
    new token from the saved credentials.
    """
    token_requests = 0

    def handler(request: Request) -> Response:
        nonlocal token_requests
        token_requests += 1
        return Response(
            json.dumps({"access_token": ACCESS_TOKEN, "expires_in": 1}),
            content_type="application/json",
        )

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler)
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthClientCredentials(
            client_secret=CLIENT_SECRET, scope=SCOPE
        ),
    ) as client:
        await client.collections.list_all()
        first = token_requests
        await asyncio.sleep(3)  # refresh interval is max(expires_in - 30, 1) -> 1s
        assert token_requests > first  # a fresh token was fetched with the credentials


def _reject_refreshes(weaviate_auth_mock: HTTPServer) -> List[float]:
    """Make the IdP reject every refresh (400 invalid_grant); returns the hit timestamps."""
    hits: List[float] = []

    def handler(request: Request) -> Response:
        hits.append(time.monotonic())
        return Response(
            json.dumps({"error": "invalid_grant", "error_description": "refresh token expired"}),
            status=400,
            content_type="application/json",
        )

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler)
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})
    return hits


def _assert_backed_off(hits: List[float], recwarn) -> None:
    # attempts at ~1s, ~2s, ~4s after connect: a fixed 1s retry would have made 5 in 5s
    assert 2 <= len(hits) <= 3
    gaps = [b - a for a, b in zip(hits, hits[1:])]
    assert all(later > earlier * 1.5 for earlier, later in zip(gaps, gaps[1:]))
    failed = [w for w in recwarn if str(w.message).startswith("Con001")]
    assert len(failed) == len(hits)  # one warning per failed attempt
    assert "invalid_grant" in str(failed[0].message)
    assert "retrying in 1s" in str(failed[0].message)
    assert "retrying in 2s" in str(failed[1].message)
    assert "unstable internet" not in str(failed[0].message)


@pytest.mark.asyncio
async def test_token_refresh_backs_off_on_persistent_failure_async(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    """A permanently failing refresh must neither kill the refresher nor hot-loop the IdP.

    A 400 invalid_grant makes authlib raise OAuthError: warn, back off exponentially,
    stay alive.
    """
    hits = _reject_refreshes(weaviate_auth_mock)

    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            expires_in=1,  # force an immediate (and failing) refresh
        ),
    ) as client:
        task = getattr(client._connection, "_ConnectionBase__token_refresh_task")  # noqa: B009
        assert task is not None
        await asyncio.sleep(5)
        assert not task.done()  # the refresher survived the failures
        await client.collections.list_all()  # ... and the client still works

    _assert_backed_off(hits, recwarn)
    # the task ended by close()'s cancellation, not by dying on the exception
    assert [w for w in recwarn if str(w.message).startswith("Con003")] == []


def test_token_refresh_backs_off_on_persistent_failure(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    """Sync colour of the test above.

    The daemon thread used to die silently on anything but an httpx.HTTPError; now it
    warns and backs off like the async task.
    """
    hits = _reject_refreshes(weaviate_auth_mock)

    threads_before = set(threading.enumerate())
    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    ) as client:
        refreshers = [
            t for t in set(threading.enumerate()) - threads_before if t.name == "TokenRefresh"
        ]
        assert len(refreshers) == 1
        time.sleep(5)
        assert refreshers[0].is_alive()  # survived the failures
        client.collections.list_all()

    _assert_backed_off(hits, recwarn)
    refreshers[0].join(timeout=2)
    assert not refreshers[0].is_alive()  # close() stops the daemon thread promptly


class _Boom(BaseException):
    """Escapes the refresh loop's `except Exception` like a real BaseException would."""


@pytest.mark.asyncio
async def test_token_refresh_death_is_surfaced_through_real_connect(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    """A refresher started by connect() that dies outside the loop body must warn (Con003).

    Pins the done-callback wiring in _create_background_token_refresh, which the
    callback-only unit test below cannot see.
    """
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    async def boom(*args, **kwargs):
        raise _Boom("boom")

    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    ) as client:
        task = getattr(client._connection, "_ConnectionBase__token_refresh_task")  # noqa: B009
        assert task is not None
        client._connection._client.refresh_token = boom  # type: ignore[union-attr]
        await asyncio.sleep(2)  # the first refresh is due after ~1s
        assert task.done() and not task.cancelled()

    stopped = [w for w in recwarn if str(w.message).startswith("Con003")]
    assert len(stopped) == 1
    assert "_Boom" in str(stopped[0].message)


@pytest.mark.asyncio
async def test_failed_connect_cancels_the_refresher_and_close_is_safe_after(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """A failed connect() must not leave the refresher running; close() after it is safe.

    The OIDC step starts the refresher before /v1/meta is checked, and close() afterwards
    (even twice) must neither hang nor raise.
    """
    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )
    # oneshot handlers take precedence over the fixture's permanent /v1/meta handler
    weaviate_auth_mock.expect_oneshot_request("/v1/meta").respond_with_response(
        Response(status=500)
    )

    tasks_before = asyncio.all_tasks()
    client = weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=500
        ),
    )
    with pytest.raises(UnexpectedStatusCodeError):
        await client.connect()

    refresh_tasks = [
        t for t in asyncio.all_tasks() - tasks_before if "token_refresh" in repr(t.get_coro())
    ]
    assert len(refresh_tasks) == 1  # it was started ...
    await asyncio.sleep(0)
    assert refresh_tasks[0].cancelled()  # ... and cancelled by the failed connect

    await asyncio.wait_for(client.close(), timeout=2)
    await asyncio.wait_for(client.close(), timeout=2)


@pytest.mark.asyncio
async def test_token_refresh_death_outside_loop_body_is_surfaced() -> None:
    """A refresher that dies where the loop body cannot catch it must still warn.

    Nothing awaits the task while it runs (close() only gathers it, exceptions included),
    so the done-callback is the only thing that can observe such a death.
    """
    on_done = getattr(_ConnectionBase, "_ConnectionBase__warn_if_token_refresh_died")  # noqa: B009

    async def dies() -> None:
        raise ValueError("boom")

    async def forever() -> None:
        await asyncio.sleep(3600)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        task = asyncio.get_running_loop().create_task(dies())
        task.add_done_callback(on_done)
        await asyncio.sleep(0)
        await asyncio.sleep(0)  # let the done-callback run

    stopped = [w for w in caught if str(w.message).startswith("Con003")]
    assert len(stopped) == 1
    assert "boom" in str(stopped[0].message)

    # a cancelled refresher (the normal close() path) must stay quiet
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        task = asyncio.get_running_loop().create_task(forever())
        task.add_done_callback(on_done)
        task.cancel()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    assert [w for w in caught if str(w.message).startswith("Con003")] == []


@pytest.mark.parametrize("header_name", ["Authorization", "authorization"])
def test_auth_header_priority(
    recwarn, weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, header_name: str
) -> None:
    """Test that auth_credentials has priority over the auth header."""
    # testing for warnings can be flaky without this as there are open SSL conections
    warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

    bearer_token = "OTHER TOKEN"

    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )

    def handler(request: Request):
        assert request.headers["Authorization"] == "Bearer " + ACCESS_TOKEN
        return Response(json.dumps({"classes": []}))

    weaviate_auth_mock.expect_request("/v1/schema").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            access_token=ACCESS_TOKEN, refresh_token="SOMETHING"
        ),
        headers={header_name: "Bearer " + bearer_token},
    ) as client:
        client.collections.list_all()  # some call that includes authorization

    weaviate_auth_mock.check_assertions()

    w = [w for w in recwarn if str(w.message).startswith("Auth004")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_refresh(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    """Test that refresh tokens are used to get a new access token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    weaviate_auth_mock.expect_request(
        "/auth",
        data=f"grant_type=refresh_token&refresh_token={REFRESH_TOKEN}&client_id={CLIENT_ID}",
    ).respond_with_json(
        {
            "access_token": ACCESS_TOKEN,
            "expires_in": 1,
            "refresh_token": REFRESH_TOKEN + str(time.time()),
        }
    )
    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    ) as client:
        # client gets a new token 5s before expiration
        client.collections.list_all()  # some call that includes authorization
    weaviate_auth_mock.check_assertions()


@pytest.mark.asyncio
async def test_refresh_async(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """Test that refresh tokens are used to get a new access token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    weaviate_auth_mock.expect_request(
        "/auth",
        data=f"grant_type=refresh_token&refresh_token={REFRESH_TOKEN}&client_id={CLIENT_ID}",
    ).respond_with_json(
        {
            "access_token": ACCESS_TOKEN,
            "expires_in": 1,
            "refresh_token": REFRESH_TOKEN + str(time.time()),
        }
    )
    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    ) as client:
        # client gets a new token 5s before expiration
        await client.collections.list_all()  # some call that includes authorization
    weaviate_auth_mock.check_assertions()


@pytest.mark.asyncio
async def test_async_auth_starts_no_threads(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """The async client must refresh tokens with an asyncio task, not threads.

    Under WASM/Pyodide threads cannot start at all, so the TokenRefresh daemon thread
    and the event-loop sidecar thread would make every async OIDC flow crash connect().
    """
    import threading

    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})
    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {
            "access_token": ACCESS_TOKEN,
            "expires_in": 500,
            "refresh_token": REFRESH_TOKEN,
        }
    )

    # compare thread OBJECTS, not names: earlier sync tests leave stale TokenRefresh
    # daemon threads alive, which would mask a regression in a name-set comparison
    threads_before = set(threading.enumerate())
    tasks_before = asyncio.all_tasks()
    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=500
        ),
    ) as client:
        await client.collections.list_all()
        new_thread_names = {t.name for t in set(threading.enumerate()) - threads_before}
        assert "TokenRefresh" not in new_thread_names
        assert "eventLoop" not in new_thread_names
        refresh_tasks = [
            t for t in asyncio.all_tasks() - tasks_before if "token_refresh" in repr(t.get_coro())
        ]
        assert len(refresh_tasks) == 1  # the refresher runs as an asyncio task instead
    # ... and close() must cancel it AND await it: done as soon as close() returns
    assert refresh_tasks[0].done()


def test_sync_reconnect_leaves_exactly_one_refresher_thread(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """close() must end the daemon thread promptly, and a later connect() must not revive it.

    The thread used to re-read the connection's shutdown event on every loop, so after
    close()+connect() it picked up the NEW (unset) event and kept refreshing next to the
    new thread — two refreshers per client.
    """
    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    def refreshers() -> List[threading.Thread]:
        return [t for t in set(threading.enumerate()) - threads_before if t.name == "TokenRefresh"]

    threads_before = set(threading.enumerate())
    client = weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=500
        ),
    )
    (first,) = refreshers()
    client.close()
    first.join(timeout=2)
    assert not first.is_alive()  # not asleep until the next (470s away) wake-up

    client.connect()
    client.collections.list_all()
    alive = [t for t in refreshers() if t.is_alive()]
    assert len(alive) == 1 and alive[0] is not first
    client.close()
    alive[0].join(timeout=2)
    assert not alive[0].is_alive()


def test_refresh_of_refresh(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    """Test that refresh tokens are used to get a new refresh token token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    # the handler will return a new refresh token with each call and asserts that the new token is used
    refresh_calls = 0

    def handler(request: Request) -> Response:
        nonlocal refresh_calls
        data = request.data.decode("utf-8")
        assert f"refresh_token={REFRESH_TOKEN}{refresh_calls}" in data

        refresh_calls += 1
        return Response(
            json.dumps(
                {
                    "access_token": ACCESS_TOKEN,
                    "expires_in": 1,
                    "refresh_token": REFRESH_TOKEN + str(refresh_calls),
                }
            )
        )

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN + str(refresh_calls), expires_in=1
        ),
    ) as client:
        # client gets a new token 5s before expiration
        time.sleep(5)
        client.collections.list_all()

    # make sure that refresh token was actually refreshed and used again
    assert refresh_calls > 1
    weaviate_auth_mock.check_assertions()


@pytest.mark.asyncio
async def test_refresh_of_refresh_async(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """Test that refresh tokens are used to get a new refresh token token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({"classes": []})

    # the handler will return a new refresh token with each call and asserts that the new token is used
    refresh_calls = 0

    def handler(request: Request) -> Response:
        nonlocal refresh_calls
        data = request.data.decode("utf-8")
        assert f"refresh_token={REFRESH_TOKEN}{refresh_calls}" in data

        refresh_calls += 1
        return Response(
            json.dumps(
                {
                    "access_token": ACCESS_TOKEN,
                    "expires_in": 1,
                    "refresh_token": REFRESH_TOKEN + str(refresh_calls),
                }
            )
        )

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler)

    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN + str(refresh_calls), expires_in=1
        ),
    ) as client:
        # client gets a new token 5s before expiration
        await asyncio.sleep(5)
        await client.collections.list_all()

    # make sure that refresh token was actually refreshed and used again
    assert refresh_calls > 1
    weaviate_auth_mock.check_assertions()


def test_auth_header_without_weaviate_auth(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """Test that setups that use the Authorization header to authorize to non-weaviate servers."""
    bearer_token = "OTHER TOKEN"
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + bearer_token}
    ).respond_with_json({"classes": []})

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        headers={"Authorization": "Bearer " + bearer_token},
    ) as client:
        client.collections.list_all()  # some call that includes authorization
    weaviate_mock.check_assertions()


def test_auth_header_with_catchall_proxy(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    """Test that the client can handle situations in which a proxy returns a catchall page for all requests."""
    weaviate_mock.expect_request("/v1/schema").respond_with_json({"classes": []})
    weaviate_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_data(
        "JsonCannotParseThis"
    )

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthClientPassword(
            username="test-username", password="test-password"
        ),
    ) as client:
        client.collections.list_all()  # some call that includes authorization
    weaviate_mock.check_assertions()

    w = [w for w in recwarn if str(w.message).startswith("Auth005")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_missing_scope(weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    with pytest.raises(MissingScopeException):
        weaviate.connect_to_local(
            host=MOCK_IP,
            port=MOCK_PORT,
            grpc_port=MOCK_PORT_GRPC,
            auth_credentials=weaviate.auth.AuthClientCredentials(
                client_secret=CLIENT_SECRET, scope=None
            ),
        )


def test_token_refresh_timeout(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    """Test that the token refresh background thread can handle timeouts of the auth server."""
    first_request = True

    # This handler lets the refresh request timeout for the first time. Then, the client retries the refresh which
    # should succeed.
    def handler(request: Request):
        nonlocal first_request
        if first_request:
            time.sleep(6)  # Timeout for auth connections is 5s. We need to wait longer
            first_request = False
        return Response(json.dumps({"access_token": ACCESS_TOKEN + "_1", "expires_in": 31}))

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler)

    # This handler only accepts the refreshed token, to make sure that the refresh happened
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN + "_1"}
    ).respond_with_json({"classes": []})

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            expires_in=1,  # force immediate refresh
        ),
    ) as client:
        time.sleep(9)  # sleep longer than the timeout, to give client time to retry
        client.collections.list_all()
    weaviate_auth_mock.check_assertions()

    w = [w for w in recwarn if str(w.message).startswith("Con001")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


@pytest.mark.asyncio
async def test_token_refresh_timeout_async(
    weaviate_auth_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    """Test that the token refresh background thread can handle timeouts of the auth server."""
    first_request = True

    # This handler lets the refresh request timeout for the first time. Then, the client retries the refresh which
    # should succeed.
    def handler(request: Request):
        nonlocal first_request
        if first_request:
            time.sleep(6)  # Timeout for auth connections is 5s. We need to wait longer
            first_request = False
        return Response(json.dumps({"access_token": ACCESS_TOKEN + "_1", "expires_in": 31}))

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler)

    # This handler only accepts the refreshed token, to make sure that the refresh happened
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN + "_1"}
    ).respond_with_json({"classes": []})

    async with weaviate.use_async_with_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthBearerToken(
            ACCESS_TOKEN,
            refresh_token=REFRESH_TOKEN,
            expires_in=1,  # force immediate refresh
        ),
    ) as client:
        await asyncio.sleep(9)  # sleep longer than the timeout, to give client time to retry
        await client.collections.list_all()
    weaviate_auth_mock.check_assertions()

    w = [w for w in recwarn if str(w.message).startswith("Con001")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


@pytest.mark.parametrize(
    "api_key",
    [
        "Super-secret-key",
        weaviate.auth.AuthApiKey(api_key="Super-secret-key"),
    ],
)
def test_with_simple_auth_no_oidc_via_api_key(
    weaviate_mock: HTTPServer,
    start_grpc_server: grpc.Server,
    recwarn,
    api_key: Union[str, weaviate.auth.AuthApiKey],
) -> None:
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + "Super-secret-key"}
    ).respond_with_json({"classes": []})

    client = weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=api_key,
    )
    client.collections.list_all()

    weaviate_mock.check_assertions()

    w = [
        w for w in recwarn if str(w.message).startswith("Auth") or str(w.message).startswith("Con")
    ]
    assert len(w) == 0


def test_with_simple_auth_no_oidc_via_additional_headers(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + "Super-secret-key"}
    ).respond_with_json({"classes": []})

    with weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        headers={"Authorization": "Bearer " + "Super-secret-key"},
    ) as client:
        client.collections.list_all()

    weaviate_mock.check_assertions()

    w = [
        w for w in recwarn if str(w.message).startswith("Auth") or str(w.message).startswith("Con")
    ]
    assert len(w) == 0

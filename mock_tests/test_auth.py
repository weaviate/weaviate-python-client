import asyncio
import json
import time
import warnings

import grpc
import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC, CLIENT_ID
from weaviate.exceptions import MissingScopeException

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
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1  # force immediate refresh
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
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1  # force immediate refresh
        ),
    ) as client:
        await asyncio.sleep(9)  # sleep longer than the timeout, to give client time to retry
        await client.collections.list_all()
    weaviate_auth_mock.check_assertions()

    w = [w for w in recwarn if str(w.message).startswith("Con001")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_with_simple_auth_no_oidc_via_api_key(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server, recwarn
) -> None:
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + "Super-secret-key"}
    ).respond_with_json({"classes": []})

    client = weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        auth_credentials=weaviate.auth.AuthApiKey(api_key="Super-secret-key"),
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

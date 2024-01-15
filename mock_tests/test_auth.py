import json
import time
import warnings

import pytest
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL, CLIENT_ID
from weaviate.exceptions import MissingScopeException

ACCESS_TOKEN = "HELLO!IamAnAccessToken"
CLIENT_SECRET = "SomeSecret.DontTell"
SCOPE = "IcanBeAnything"
REFRESH_TOKEN = "UseMeToRefreshYourAccessToken"


def test_user_password(weaviate_auth_mock):
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
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL, auth_client_secret=weaviate.AuthClientPassword(user, pw)
    )
    client.schema.delete_all()  # some call that includes authorization


def test_bearer_token(weaviate_auth_mock):
    """Test that client sends the given bearer token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthBearerToken(ACCESS_TOKEN, refresh_token=REFRESH_TOKEN),
    )
    client.schema.delete_all()  # some call that includes authorization


def test_client_credentials(weaviate_auth_mock):
    """Test that client sends the client credentials to the token endpoint and uses the correct token."""
    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500}
    )
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthClientCredentials(client_secret=CLIENT_SECRET, scope=SCOPE),
    )
    client.schema.delete_all()  # some call that includes authorization


@pytest.mark.parametrize("header_name", ["Authorization", "authorization"])
def test_auth_header_priority(recwarn, weaviate_auth_mock, header_name: str):
    """Test that auth_client_secret has priority over the auth header."""

    # testing for warnings can be flaky without this as there are open SSL conections
    warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

    bearer_token = "OTHER TOKEN"

    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )

    def handler(request: Request):
        assert request.headers["Authorization"] == "Bearer " + ACCESS_TOKEN
        return Response(json.dumps({}))

    weaviate_auth_mock.expect_request("/v1/schema").respond_with_handler(handler)

    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthBearerToken(
            access_token=ACCESS_TOKEN, refresh_token="SOMETHING"
        ),
        additional_headers={header_name: "Bearer " + bearer_token},
    )
    client.schema.delete_all()  # some call that includes authorization

    w = [w for w in recwarn if str(w.message).startswith("Auth004")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_refresh(weaviate_auth_mock):
    """Test that refresh tokens are used to get a new access token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    weaviate_auth_mock.expect_request(
        "/auth",
        data=f"grant_type=refresh_token&refresh_token={REFRESH_TOKEN}&client_id={CLIENT_ID}",
    ).respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 1, "refresh_token": REFRESH_TOKEN}
    )
    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    )
    # client gets a new token 5s before expiration
    client.schema.delete_all()  # some call that includes authorization


def test_auth_header_without_weaviate_auth(weaviate_mock):
    """Test that setups that use the Authorization header to authorize to non-weaviate servers."""
    bearer_token = "OTHER TOKEN"
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + bearer_token}
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL,
        additional_headers={"Authorization": "Bearer " + bearer_token},
    )
    client.schema.delete_all()  # some call that includes authorization


def test_auth_header_with_catchall_proxy(weaviate_mock, recwarn):
    """Test that the client can handle situations in which a proxy returns a catchall page for all requests."""
    weaviate_mock.expect_request("/v1/schema").respond_with_json({})
    weaviate_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_data(
        "JsonCannotParseThis"
    )

    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthClientPassword(
            username="test-username", password="test-password"
        ),
    )
    client.schema.delete_all()  # some call that includes authorization

    w = [w for w in recwarn if str(w.message).startswith("Auth005")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_missing_scope(weaviate_auth_mock):
    with pytest.raises(MissingScopeException):
        weaviate.Client(
            MOCK_SERVER_URL,
            auth_client_secret=weaviate.AuthClientCredentials(
                client_secret=CLIENT_SECRET, scope=None
            ),
        )


def test_token_refresh_timeout(weaviate_auth_mock, recwarn):
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
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1  # force immediate refresh
        ),
    )

    time.sleep(9)  # sleep longer than the timeout, to give client time to retry
    client.schema.delete_all()

    w = [w for w in recwarn if str(w.message).startswith("Con001")]
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)


def test_with_simple_auth_no_oidc_via_api_key(weaviate_mock, recwarn):
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + "Super-secret-key"}
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthApiKey(api_key="Super-secret-key"),
    )
    client.schema.delete_all()

    weaviate_mock.check_assertions()

    w = [
        w for w in recwarn if str(w.message).startswith("Auth") or str(w.message).startswith("Con")
    ]
    assert len(w) == 0


def test_with_simple_auth_no_oidc_via_additional_headers(weaviate_mock, recwarn):
    weaviate_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + "Super-secret-key"}
    ).respond_with_json({})

    client = weaviate.Client(
        MOCK_SERVER_URL,
        additional_headers={"Authorization": "Bearer " + "Super-secret-key"},
    )
    client.schema.delete_all()

    weaviate_mock.check_assertions()

    w = [
        w for w in recwarn if str(w.message).startswith("Auth") or str(w.message).startswith("Con")
    ]
    assert len(w) == 0

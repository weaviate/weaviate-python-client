import json
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
        data=f"grant_type=password&username={user}&password={pw}&scope=offline_access&client_id={CLIENT_ID}",
    ).respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500, "refresh_token": REFRESH_TOKEN}
    )
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    client = weaviate.Client(
        url=MOCK_SERVER_URL, auth_client_secret=weaviate.AuthClientPassword(user, pw)
    )
    client.schema.delete_all()  # some call that includes authorization


def test_bearer_token(weaviate_auth_mock):
    """Test that client sends the given bearer token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    client = weaviate.Client(
        url=MOCK_SERVER_URL,
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
        url=MOCK_SERVER_URL,
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
        url=MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthBearerToken(
            access_token=ACCESS_TOKEN, refresh_token="SOMETHING"
        ),
        additional_headers={header_name: "Bearer " + bearer_token},
    )
    client.schema.delete_all()  # some call that includes authorization

    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, UserWarning)
    assert str(w.message).startswith("Auth004")


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
        url=MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthBearerToken(
            ACCESS_TOKEN, refresh_token=REFRESH_TOKEN, expires_in=1
        ),
    )
    # client gets a new token 5s before expiration
    client.schema.delete_all()  # some call that includes authorization


def test_missing_scope(weaviate_auth_mock):
    with pytest.raises(MissingScopeException):
        weaviate.Client(
            url=MOCK_SERVER_URL,
            auth_client_secret=weaviate.AuthClientCredentials(
                client_secret=CLIENT_SECRET, scope=None
            ),
        )

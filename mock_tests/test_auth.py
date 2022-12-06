import pytest

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL, CLIENT_ID

ACCESS_TOKEN = "HELLO!IamAnAccessToken"
CLIENT_SECRET = "SomeSecret.DontTell"
SCOPE = "IcanBeAnything"


def test_user_password(weaviate_auth_mock):
    """Test that client sends username and pw with the correct body to the token endpoint and uses the correct token."""

    user = "AUsername"
    pw = "SomePassWord"

    # note: order matters. If this handler is not called, check of the order of arguments changed
    weaviate_auth_mock.expect_request(
        "/auth",
        data=f"grant_type=password&username={user}&password={pw}&scope=offline_access&client_id={CLIENT_ID}",
    ).respond_with_json({"access_token": ACCESS_TOKEN, "expires_in": 500})
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
        url=MOCK_SERVER_URL, auth_client_secret=weaviate.AuthBearerToken(ACCESS_TOKEN)
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
def test_auth_header_priority(weaviate_auth_mock, header_name: str):
    """Test that the auth header has priority over other authentication methods."""
    bearer_token = "OTHER TOKEN"

    weaviate_auth_mock.expect_request("/auth").respond_with_json(
        {"access_token": ACCESS_TOKEN, "expires_in": 500}
    )
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + bearer_token}
    ).respond_with_json({})

    client = weaviate.Client(
        url=MOCK_SERVER_URL,
        auth_client_secret=weaviate.AuthClientCredentials(client_secret=CLIENT_SECRET, scope=SCOPE),
        additional_headers={header_name: "Bearer " + bearer_token},
    )
    client.schema.delete_all()  # some call that includes authorization

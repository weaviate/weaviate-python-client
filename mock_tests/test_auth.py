import json

import pytest
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import CLIENT_ID

ACCESS_TOKEN = "HELLO!IamAnAccessToken"
CLIENT_SECRET = "SomeSecret.DontTell"
SCOPE = "IcanBeAnything"


def test_user_password(weaviate_auth_mock):
    """Test that client sends username and pw with the correct body to the token endpoint and uses the correct token."""

    user = "AUsername"
    pw = "SomePassWord"

    weaviate_auth_mock.expect_request(
        "/auth", data=f"grant_type=password&client_id={CLIENT_ID}&username={user}&password={pw}"
    ).respond_with_json({"access_token": ACCESS_TOKEN, "expires_in": 500})
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    client = weaviate.Client(
        url="http://127.0.0.1:23534", auth_client_secret=weaviate.AuthClientPassword(user, pw)
    )
    client.schema.delete_all()  # some call that includes authorization


def test_bearer_token(weaviate_auth_mock):
    """Test that client sends the given bearer token."""
    weaviate_auth_mock.expect_request(
        "/v1/schema", headers={"Authorization": "Bearer " + ACCESS_TOKEN}
    ).respond_with_json({})

    client = weaviate.Client(
        url="http://127.0.0.1:23534", auth_client_secret=weaviate.AuthBearerConfig(ACCESS_TOKEN)
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
        url="http://127.0.0.1:23534",
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
        url="http://127.0.0.1:23534",
        auth_client_secret=weaviate.AuthClientCredentials(client_secret=CLIENT_SECRET, scope=SCOPE),
        additional_headers={header_name: "Bearer " + bearer_token},
    )
    client.schema.delete_all()  # some call that includes authorization


def test_refresh(weaviate_auth_mock):
    """Test that the header is refreshed and a new token is acquired before expiration.

    The client reduces the expiration-time by 2s, therefore every calls results in a new access token."""
    number_of_calls = 0

    def handler_auth(_: Request):
        return Response(
            json.dumps({"access_token": ACCESS_TOKEN + "_" + str(number_of_calls), "expires_in": 1})
        )

    weaviate_auth_mock.expect_request("/auth").respond_with_handler(handler_auth)

    def handler_schema(request: Request):
        nonlocal number_of_calls
        number_of_calls_in_header = int(request.headers["authorization"].split("_")[-1])
        assert number_of_calls_in_header == number_of_calls
        number_of_calls += 1
        return Response(json.dumps({}))

    weaviate_auth_mock.expect_request("/v1/schema").respond_with_handler(handler_schema)

    client = weaviate.Client(
        url="http://127.0.0.1:23534",
        auth_client_secret=weaviate.AuthClientCredentials(client_secret=CLIENT_SECRET, scope=SCOPE),
    )
    for _ in range(5):
        client.schema.delete_all()

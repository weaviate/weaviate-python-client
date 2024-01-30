import os
from typing import Dict, Optional

import httpx
import pytest
from _pytest.fixtures import SubRequest

import weaviate
import weaviate.classes as wvc
from integration.conftest import _sanitize_collection_name
from weaviate import util
from weaviate.collections.classes.config import DataType, Property
from weaviate.collections.classes.filters import Filter
from weaviate.exceptions import AuthenticationFailedError, UnexpectedStatusCodeError

ANON_PORT = 8080
AZURE_PORT = 8081
OKTA_PORT_CC = 8082
OKTA_PORT_USERS = 8083
WCS_PORT = 8085
WCS_PORT_GRPC = 50056


def is_auth_enabled(url: str) -> bool:
    response = httpx.get("http://" + url + "/v1/.well-known/openid-configuration")
    return response.status_code == 200


def test_no_auth_provided() -> None:
    """Test exception when trying to access a weaviate that requires authentication."""
    assert is_auth_enabled(f"localhost:{AZURE_PORT}")
    with pytest.raises(AuthenticationFailedError):
        weaviate.connect_to_local(port=AZURE_PORT)


@pytest.mark.parametrize(
    "name,env_variable_name,port,scope",
    [
        ("azure", "AZURE_CLIENT_SECRET", AZURE_PORT, None),
        (
            "azure",
            "AZURE_CLIENT_SECRET",
            AZURE_PORT,
            "4706508f-30c2-469b-8b12-ad272b3de864/.default",
        ),
        ("okta", "OKTA_CLIENT_SECRET", OKTA_PORT_CC, "some_scope"),
    ],
)
def test_authentication_client_credentials(
    name: str, env_variable_name: str, port: int, scope: Optional[str]
) -> None:
    """Test client credential flow with various providers."""
    client_secret = os.environ.get(env_variable_name)
    if client_secret is None:
        pytest.skip(f"No {name} login data found.")

    assert is_auth_enabled(f"localhost:{port}")

    with weaviate.connect_to_local(
        port=port,
        auth_credentials=wvc.init.Auth.client_credentials(client_secret=client_secret, scope=scope),
    ) as client:
        client.collections.list_all()  # no exception


@pytest.mark.parametrize(
    "name,user,env_variable_name,port,scope,warning",
    [
        (
            "WCS",
            "ms_2d0e007e7136de11d5f29fce7a53dae219a51458@existiert.net",
            "WCS_DUMMY_CI_PW",
            WCS_PORT,
            None,
            False,
        ),
        (
            "okta",
            "test@test.de",
            "OKTA_DUMMY_CI_PW",
            OKTA_PORT_USERS,
            "some_scope offline_access",
            False,
        ),
        (
            "okta - no refresh",
            "test@test.de",
            "OKTA_DUMMY_CI_PW",
            OKTA_PORT_USERS,
            "some_scope",
            True,
        ),
    ],
)
def test_authentication_user_pw(
    recwarn: pytest.WarningsRecorder,
    name: str,
    user: str,
    env_variable_name: str,
    port: int,
    scope: str,
    warning: bool,
) -> None:
    """Test authentication using Resource Owner Password Credentials Grant (User + PW)."""
    assert is_auth_enabled(f"localhost:{port}")

    pw = os.environ.get(env_variable_name)
    if pw is None:
        pytest.skip(f"No login data for {name} found.")

    if scope is not None:
        auth = wvc.init.Auth.client_password(username=user, password=pw, scope=scope)
    else:
        auth = wvc.init.Auth.client_password(username=user, password=pw)

    with weaviate.connect_to_local(port=port, auth_credentials=auth) as client:
        client.collections.list_all()  # no exception

        if warning:
            assert len(recwarn) == 1
            w = recwarn.pop()
            assert issubclass(w.category, UserWarning)
            assert str(w.message).startswith("Auth002")
        else:
            assert len(recwarn) == 0


def test_client_with_authentication_with_anon_weaviate() -> None:
    """Test that we warn users when their client has auth enabled, but weaviate has only anon access."""

    assert not is_auth_enabled(f"localhost:{ANON_PORT}")

    auth = wvc.init.Auth.client_password(username="someUser", password="SomePw")
    with pytest.warns(UserWarning) as recwarn:
        with weaviate.connect_to_local(auth_credentials=auth) as client:
            client.collections.list_all()
        assert len(recwarn) == 1
        assert str(recwarn.list[0].message).startswith("Auth001")


def _get_access_token(url: str, user: str, pw: str) -> Dict[str, str]:
    # get an access token with WCS user and pw.
    weaviate_open_id_config = httpx.get("http://" + url + "/v1/.well-known/openid-configuration")
    response_json = weaviate_open_id_config.json()
    client_id = response_json["clientId"]
    href = response_json["href"]

    # Get the token issuer's OIDC configuration
    response_auth = httpx.get(href)

    # Construct the POST request to send to 'token_endpoint'
    auth_body = {
        "grant_type": "password",
        "client_id": client_id,
        "username": user,
        "password": pw,
        "scope": "openid offline_access",
    }
    response_post = httpx.post(url=response_auth.json()["token_endpoint"], data=auth_body)
    resp_typed = util._decode_json_response_dict(response_post, "test")
    assert resp_typed is not None
    return resp_typed


@pytest.mark.parametrize(
    "name,user,env_variable_name,port",
    [
        (
            "WCS",
            "ms_2d0e007e7136de11d5f29fce7a53dae219a51458@existiert.net",
            "WCS_DUMMY_CI_PW",
            WCS_PORT,
        ),
        (
            "okta",
            "test@test.de",
            "OKTA_DUMMY_CI_PW",
            OKTA_PORT_USERS,
        ),
    ],
)
def test_authentication_with_bearer_token(
    name: str, user: str, env_variable_name: str, port: int
) -> None:
    """Test authentication using existing bearer token."""
    url = f"localhost:{port}"
    assert is_auth_enabled(url)
    pw = os.environ.get(env_variable_name)
    if pw is None:
        pytest.skip(f"No login data for {name} found.")

    # use token to authenticate
    token = _get_access_token(url, user, pw)
    auth = wvc.init.Auth.bearer_token(
        access_token=token["access_token"],
        expires_in=int(token["expires_in"]),
        refresh_token=token["refresh_token"],
    )
    with weaviate.connect_to_local(port=port, auth_credentials=auth) as client:
        client.collections.list_all()


def test_authentication_with_bearer_token_no_refresh() -> None:
    """Test authentication using existing bearer token."""
    url = f"localhost:{OKTA_PORT_USERS}"
    assert is_auth_enabled(url)
    pw = os.environ.get("OKTA_DUMMY_CI_PW")
    if pw is None:
        pytest.skip("No login data for found.")

    # use token to authenticate
    token = _get_access_token(url, "test@test.de", pw)
    auth = wvc.init.Auth.bearer_token(
        access_token=token["access_token"],
        expires_in=int(token["expires_in"]),
    )
    with pytest.warns(UserWarning) as recwarn:
        with weaviate.connect_to_local(port=OKTA_PORT_USERS, auth_credentials=auth) as client:
            client.collections.list_all()
        assert len(recwarn) == 1
        assert str(recwarn.list[0].message).startswith("Auth002")


def test_api_key() -> None:
    assert is_auth_enabled(f"localhost:{WCS_PORT}")
    with weaviate.connect_to_local(
        port=WCS_PORT, auth_credentials=wvc.init.Auth.api_key(api_key="my-secret-key")
    ) as client:
        client.collections.list_all()


@pytest.mark.parametrize("header_name", ["Authorization", "authorization"])
def test_api_key_in_header(header_name: str) -> None:
    assert is_auth_enabled(f"localhost:{WCS_PORT}")
    with weaviate.connect_to_local(
        port=WCS_PORT, headers={header_name: "Bearer my-secret-key"}
    ) as client:
        client.collections.list_all()


def test_api_key_wrong_key() -> None:
    assert is_auth_enabled(f"localhost:{WCS_PORT}")

    with pytest.raises(UnexpectedStatusCodeError) as e:
        weaviate.connect_to_local(
            port=WCS_PORT, auth_credentials=wvc.init.Auth.api_key(api_key="my-secret-key-wrong")
        )
    assert e.value.status_code == 401


def test_auth_e2e(request: SubRequest) -> None:
    name = _sanitize_collection_name(request.node.name)
    url = f"localhost:{WCS_PORT}"
    assert is_auth_enabled(url)

    with weaviate.connect_to_local(
        port=WCS_PORT,
        grpc_port=WCS_PORT_GRPC,
        auth_credentials=wvc.init.Auth.api_key(api_key="my-secret-key"),
    ) as client:
        client.collections.delete(name)
        col = client.collections.create(
            name=name,
            description="test",
            properties=[
                Property(name="name", data_type=DataType.TEXT),
            ],
        )
        col.data.insert({"name": "test"})
        col.data.insert_many([{"name": "test2"}])
        assert len(col.query.fetch_objects().objects) == 2

        col.data.delete_many(Filter.by_property("name").equal("test"))
        assert len(col.query.fetch_objects().objects) == 1

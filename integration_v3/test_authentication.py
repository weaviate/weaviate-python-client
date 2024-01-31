import os
import time
import warnings
from typing import Optional, Dict

import pytest
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import HTTPError as RequestsHTTPError

import weaviate
from weaviate import (
    AuthenticationFailedException,
    AuthClientCredentials,
    AuthClientPassword,
    AuthBearerToken,
)
from weaviate.auth import AuthApiKey
from weaviate.exceptions import UnexpectedStatusCodeException

ANON_PORT = 8080
AZURE_PORT = 8081
OKTA_PORT_CC = 8082
OKTA_PORT_USERS = 8083
WCS_PORT = 8085


def wait_for_weaviate(url: str) -> None:
    ready_url = url + "/v1/.well-known/ready"
    for _i in range(5):
        try:
            requests.get(ready_url).raise_for_status()
            return
        except (RequestsHTTPError, RequestsConnectionError):
            time.sleep(1)

    try:
        requests.get(ready_url).raise_for_status()
        return
    except (RequestsHTTPError, RequestsConnectionError):
        pass
    raise ValueError


def is_auth_enabled(url: str):
    wait_for_weaviate(url)
    response = requests.get(url + "/v1/.well-known/openid-configuration")
    return response.status_code == 200


def test_no_auth_provided():
    """Test exception when trying to access a weaviate that requires authentication."""
    url = f"http://localhost:{AZURE_PORT}"
    assert is_auth_enabled(url)
    with pytest.raises(AuthenticationFailedException):
        weaviate.Client(url)


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
    name: str, env_variable_name: str, port: str, scope: Optional[str]
):
    """Test client credential flow with various providers."""
    client_secret = os.environ.get(env_variable_name)
    if client_secret is None:
        pytest.skip(f"No {name} login data found.")

    url = f"http://localhost:{port}"
    assert is_auth_enabled(url)
    client = weaviate.Client(
        url,
        auth_client_secret=AuthClientCredentials(client_secret=client_secret, scope=scope),
    )
    client.schema.delete_all()  # no exception


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
    recwarn, name: str, user: str, env_variable_name: str, port: str, scope: str, warning: bool
):
    """Test authentication using Resource Owner Password Credentials Grant (User + PW)."""
    # testing for warnings can be flaky without this as there are open SSL conections
    warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

    url = f"http://localhost:{port}"
    assert is_auth_enabled(url)

    pw = os.environ.get(env_variable_name)
    if pw is None:
        pytest.skip(f"No login data for {name} found.")

    if scope is not None:
        auth = AuthClientPassword(username=user, password=pw, scope=scope)
    else:
        auth = AuthClientPassword(username=user, password=pw)

    client = weaviate.Client(url, auth_client_secret=auth)
    client.schema.delete_all()  # no exception
    if warning:
        assert any([str(w.message).startswith("Auth002") for w in recwarn])
    else:
        assert not any([str(w.message).startswith("Auth002") for w in recwarn])


def _get_access_token(url: str, user: str, pw: str) -> Dict[str, str]:
    # get an access token with WCS user and pw.
    weaviate_open_id_config = requests.get(url + "/v1/.well-known/openid-configuration")
    response_json = weaviate_open_id_config.json()
    client_id = response_json["clientId"]
    href = response_json["href"]

    # Get the token issuer's OIDC configuration
    response_auth = requests.get(href)

    # Construct the POST request to send to 'token_endpoint'
    auth_body = {
        "grant_type": "password",
        "client_id": client_id,
        "username": user,
        "password": pw,
        "scope": "openid offline_access",
    }
    response_post = requests.post(response_auth.json()["token_endpoint"], auth_body)
    return response_post.json()


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
def test_authentication_with_bearer_token(name: str, user: str, env_variable_name: str, port: str):
    """Test authentication using existing bearer token."""
    url = f"http://localhost:{port}"
    assert is_auth_enabled(url)
    pw = os.environ.get(env_variable_name)
    if pw is None:
        pytest.skip(f"No login data for {name} found.")

    # use token to authenticate
    token = _get_access_token(url, user, pw)

    client = weaviate.Client(
        url,
        auth_client_secret=AuthBearerToken(
            access_token=token["access_token"],
            expires_in=int(token["expires_in"]),
            refresh_token=token["refresh_token"],
        ),
    )
    client.schema.delete_all()  # no exception


def test_client_with_authentication_with_anon_weaviate(recwarn):
    """Test that we warn users when their client has auth enabled, but weaviate has only anon access."""
    # testing for warnings can be flaky without this as there are open SSL conections
    warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

    url = f"http://localhost:{ANON_PORT}"
    assert not is_auth_enabled(url)

    client = weaviate.Client(
        url,
        auth_client_secret=AuthClientPassword(username="someUser", password="SomePw"),
    )

    # only one warning
    assert any([str(w.message).startswith("Auth001") for w in recwarn])

    client.schema.delete_all()  # no exception, client works


def test_bearer_token_without_refresh(recwarn):
    """Test that the client warns users when only supplying an access token without refresh."""

    # testing for warnings can be flaky without this as there are open SSL conections
    warnings.filterwarnings(action="ignore", message="unclosed", category=ResourceWarning)

    url = f"http://localhost:{WCS_PORT}"
    assert is_auth_enabled(url)
    pw = os.environ.get("WCS_DUMMY_CI_PW")
    if pw is None:
        pytest.skip("No login data for WCS found.")

    token = _get_access_token(url, "ms_2d0e007e7136de11d5f29fce7a53dae219a51458@existiert.net", pw)
    client = weaviate.Client(
        url,
        auth_client_secret=AuthBearerToken(
            access_token=token["access_token"],
        ),
    )
    client.schema.delete_all()  # no exception, client works

    assert any([str(w.message).startswith("Auth002") for w in recwarn])


def test_api_key():
    url = f"http://localhost:{WCS_PORT}"
    assert is_auth_enabled(url)

    client = weaviate.Client(url, auth_client_secret=AuthApiKey(api_key="my-secret-key"))
    client.schema.delete_all()  # no exception, client works


def test_api_key_wrong_key():
    url = f"http://localhost:{WCS_PORT}"
    assert is_auth_enabled(url)

    with pytest.raises(UnexpectedStatusCodeException) as e:
        weaviate.Client(url, auth_client_secret=AuthApiKey(api_key="wrong_key"))
        assert e.value.status_code == 401

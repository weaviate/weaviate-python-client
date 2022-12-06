import os
from typing import Optional

import pytest
import requests

import weaviate
from weaviate import AuthenticationFailedException, AuthClientCredentials, AuthClientPassword

ANON_PORT = "8080"
AZURE_PORT = "8081"
OKTA_PORT = "8082"
WCS_PORT = "8083"


def is_auth_enabled(url: str):
    response = requests.get(url + "/v1/.well-known/openid-configuration")
    return response.status_code == 200


def test_no_auth_provided():
    """Test exception when trying to access a weaviate that requires authentication."""
    url = "http://127.0.0.1:" + AZURE_PORT
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
        ("okta", "OKTA_CLIENT_SECRET", OKTA_PORT, "some_scope"),
    ],
)
def test_authentication_client_credentials(
    name: str, env_variable_name: str, port: str, scope: Optional[str]
):
    """Test client credential flow with various providers."""
    client_secret = os.environ.get(env_variable_name)
    if client_secret is None:
        pytest.skip(f"No {name} login data found.")

    url = "http://127.0.0.1:" + port
    assert is_auth_enabled(url)
    client = weaviate.Client(
        url, auth_client_secret=AuthClientCredentials(client_secret=client_secret, scope=scope)
    )
    client.schema.delete_all()  # no exception


def test_authentication_user_pw():
    """Test authentication using Resource Owner Password Credentials Grant (User + PW)."""
    url = "http://127.0.0.1:" + WCS_PORT
    assert is_auth_enabled(url)

    wcs_pw = os.environ.get("WCS_DUMMY_CI_PW")
    if wcs_pw is None:
        pytest.skip("No login data for WCS found.")

    client = weaviate.Client(
        url,
        auth_client_secret=AuthClientPassword(
            username="ms_2d0e007e7136de11d5f29fce7a53dae219a51458@existiert.net", password=wcs_pw
        ),
    )
    client.schema.delete_all()  # no exception


def test_client_with_authentication_with_anon_weaviate(recwarn):
    """Test that we warn users when their client has auth enabled, but weaviate has only anon access."""
    url = "http://127.0.0.1:" + ANON_PORT
    assert not is_auth_enabled(url)

    client = weaviate.Client(
        url,
        auth_client_secret=AuthClientPassword(username="someUser", password="SomePw"),
    )

    # only one warning
    assert len(recwarn) == 1
    w = recwarn.pop()
    assert issubclass(w.category, UserWarning)
    assert str(w.message).startswith("Auth001")

    client.schema.delete_all()  # no exception, client works

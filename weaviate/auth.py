"""
Authentication class definitions.
"""
from dataclasses import dataclass
from typing import Optional, Union

from weaviate.warnings import _Warnings


@dataclass
class AuthClientCredentials:
    """Authenticate for the Client Credential flow using client secrets.

    Acquire the client secret from your identify provider and set the appropriate scope. The client includes hardcoded
    scopes for Azure, otherwise it needs to be supplied.
    """

    client_secret: str
    scope: Optional[str] = None


@dataclass
class AuthClientPassword:
    """Using username and password for authentication with Resource Owner Password flow.

    For some providers the scope needs to contain "offline_access" (and "openid" which is automatically added) to return
    a refresh token. Without a refresh token the authentication will expire once the lifetime of the access token is up.
    """

    username: str
    password: str
    scope: Optional[str] = "offline_access"


@dataclass
class AuthBearerToken:
    """Using a preexisting bearer/access token for authentication.

    The expiration time of access tokens is given in seconds.

    Only the access token is required. However, when no refresh token is given, the authentication will expire once
    the lifetime of the access token is up.
    """

    access_token: str
    expires_in: int = 60
    refresh_token: Optional[str] = None

    def __post_init__(self):
        if self.expires_in and self.expires_in < 0:
            _Warnings.auth_negative_expiration_time(self.expires_in)


AuthCredentials = Union[AuthBearerToken, AuthClientPassword, AuthClientCredentials]

"""
Authentication class definitions.
"""
from dataclasses import dataclass, field
from typing import Optional, Union, List

from weaviate.warnings import _Warnings

SCOPES = Union[str, List[str]]


@dataclass
class AuthClientCredentials:
    """Authenticate for the Client Credential flow using client secrets.

    Acquire the client secret from your identify provider and set the appropriate scope. The client includes hardcoded
    scopes for Azure, otherwise it needs to be supplied.
    Scopes can be given as:
      - List of strings: ["scope1", "scope2"]
      - space separated string: "scope1 scope2"
    """

    client_secret: str
    scope: Optional[SCOPES] = None

    def __post_init__(self):
        if isinstance(self.scope, str):
            self.scope = self.scope.split(" ")


@dataclass
class AuthClientPassword:
    """Using username and password for authentication with Resource Owner Password flow.

    For some providers the scope needs to contain "offline_access" (and "openid" which is automatically added) to return
    a refresh token. Without a refresh token the authentication will expire once the lifetime of the access token is up.
    Scopes can be given as:
      - List of strings: ["scope1", "scope2"]
      - space separated string: "scope1 scope2"

    """

    username: str
    password: str
    scope: Optional[SCOPES] = field(default_factory=lambda: ["offline_access"])

    def __post_init__(self):
        if isinstance(self.scope, str):
            self.scope = self.scope.split(" ")


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

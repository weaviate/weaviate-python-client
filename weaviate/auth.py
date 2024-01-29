"""
Authentication class definitions.
"""

from dataclasses import dataclass
from typing import Optional, Union, List

from weaviate.warnings import _Warnings

SCOPES = Union[str, List[str]]


@dataclass
class _ClientCredentials:
    """Authenticate for the Client Credential flow using client secrets.

    Acquire the client secret from your identify provider and set the appropriate scope. The client includes hardcoded
    scopes for Azure, otherwise it needs to be supplied.
    Scopes can be given as:
      - List of strings: ["scope1", "scope2"]
      - space separated string: "scope1 scope2"
    """

    client_secret: str
    scope: Optional[SCOPES] = None

    def __post_init__(self) -> None:
        if self.scope is None:
            self.scope_list: List[str] = []
        elif isinstance(self.scope, str):
            self.scope_list = self.scope.split(" ")
        elif isinstance(self.scope, list):
            self.scope_list = self.scope


@dataclass
class _ClientPassword:
    """Using username and password for authentication with Resource Owner Password flow.

    For some providers the scope needs to contain "offline_access" (and "openid" which is automatically added) to return
    a refresh token. Without a refresh token the authentication will expire once the lifetime of the access token is up.
    Scopes can be given as:
      - List of strings: ["scope1", "scope2"]
      - space separated string: "scope1 scope2"

    """

    username: str
    password: str
    scope: Optional[SCOPES] = None

    def __post_init__(self) -> None:
        if self.scope is None:
            self.scope_list: List[str] = []
        elif isinstance(self.scope, str):
            self.scope_list = self.scope.split(" ")
        elif isinstance(self.scope, list):
            self.scope_list = self.scope


@dataclass
class _BearerToken:
    """Using a preexisting bearer/access token for authentication.

    The expiration time of access tokens is given in seconds.

    Only the access token is required. However, when no refresh token is given, the authentication will expire once
    the lifetime of the access token is up.
    """

    access_token: str
    expires_in: int = 60
    refresh_token: Optional[str] = None

    def __post_init__(self) -> None:
        if self.expires_in and self.expires_in < 0:
            _Warnings.auth_negative_expiration_time(self.expires_in)


@dataclass
class _APIKey:
    """Using the given API key to authenticate with weaviate."""

    api_key: str


class Auth:
    @staticmethod
    def api_key(api_key: str) -> _APIKey:
        return _APIKey(api_key)

    @staticmethod
    def client_credentials(
        client_secret: str, scope: Optional[SCOPES] = None
    ) -> _ClientCredentials:
        return _ClientCredentials(client_secret, scope)

    @staticmethod
    def client_password(
        username: str, password: str, scope: Optional[SCOPES] = None
    ) -> _ClientPassword:
        return _ClientPassword(username=username, password=password, scope=scope)

    @staticmethod
    def bearer_token(
        access_token: str, expires_in: int = 60, refresh_token: Optional[str] = None
    ) -> _BearerToken:
        return _BearerToken(
            access_token=access_token, expires_in=expires_in, refresh_token=refresh_token
        )


OidcAuth = Union[_BearerToken, _ClientPassword, _ClientCredentials]
AuthCredentials = Union[OidcAuth, _APIKey]

# required to ease v3 -> v4 transition
AuthApiKey = _APIKey
"""@deprecated; use wvc.Auth.api_key() instead."""
AuthBearerToken = _BearerToken
"""@deprecated; use wvc.Auth.api_key() instead."""
AuthClientCredentials = _ClientCredentials
"""@deprecated; use wvc.Auth.api_key() instead."""
AuthClientPassword = _ClientPassword
"""@deprecated; use wvc.Auth.api_key() instead."""

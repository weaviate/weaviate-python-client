"""
Authentication class definitions.
"""
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class AuthClientCredentials:
    """Authenticate for the client credential flow using client secrets.

    Acquire the client secret from your identify provider and set the appropriate scope. Rhe client includes hardcoded
    scopes for Azure, otherwise it needs to be supplied.
    """

    client_secret: str
    scope: Optional[str] = None


@dataclass
class AuthClientPassword:
    """Using username and password for authentication. In case of grant type password."""

    username: str
    password: str
    scope: Optional[str] = "offline_access"


@dataclass
class AuthBearerToken:
    """Using a preexisting bearer token for authentication."""

    bearer_token: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None


AuthCredentials = Union[AuthBearerToken, AuthClientPassword, AuthClientCredentials]

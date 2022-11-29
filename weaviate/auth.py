"""
Authentication class definitions.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class AuthCredentials:
    """Base class for authentication."""


@dataclass
class AuthClientCredentials(AuthCredentials):
    """Authenticate for the client credential flow using client secrets.

    Acquire the client secret from your identify provider and set the appropriate scope. Rhe client includes hardcoded
    scopes for Azure, otherwise it needs to be supplied.
    """

    client_secret: str
    scope: Optional[str] = None


@dataclass
class AuthClientPassword(AuthCredentials):
    """Using username and password for authentication. In case of grant type password."""

    username: str
    password: str


@dataclass
class AuthBearerConfig(AuthCredentials):
    """Using a preexisting bearer token for authentication."""

    bearer_token: str

from typing import Dict, List, Union

import httpx
import pytest

import weaviate.classes as wvc
from weaviate.connect.authentication import _Auth


@pytest.mark.parametrize("expires_in,warning", [(-1, True), (5, False)])
def test_bearer_validation(
    recwarn: pytest.WarningsRecorder, expires_in: int, warning: bool
) -> None:
    wvc.init.Auth.bearer_token(
        access_token="Doesn't matter",
        refresh_token="Doesn't matter",
        expires_in=expires_in,
    )

    if warning:
        assert len(recwarn) == 1
        w = recwarn.pop()
        assert issubclass(w.category, UserWarning)
        assert str(w.message).startswith("Auth003")
    else:
        assert len(recwarn) == 0


@pytest.fixture
def oidc_config() -> Dict[str, Union[str, List[str]]]:
    return {"href": "http://localhost:1234/.well-known", "clientId": "client-id"}


def test_oidc_session_uses_connection_transports(
    oidc_config: Dict[str, Union[str, List[str]]],
) -> None:
    """The OIDC session is the REST client, so it must use the connection's mounts and trust_env."""
    transport = httpx.HTTPTransport()
    auth = _Auth(
        oidc_config=oidc_config,
        credentials=wvc.init.Auth.bearer_token(
            access_token="Doesn't matter", refresh_token="Doesn't matter"
        ),
        make_mounts=lambda: {"http://": transport},
        trust_env=False,
        colour="sync",
    )
    auth._token_endpoint = "http://localhost:1234/token"  # so that no request is made

    with _Auth.result(auth.get_auth_session()) as session:
        assert session.trust_env is False
        assert list(session._mounts.values()) == [transport]


@pytest.mark.asyncio
async def test_oidc_session_uses_connection_transports_async(
    oidc_config: Dict[str, Union[str, List[str]]],
) -> None:
    """The async OIDC session is the REST client, too."""
    transport = httpx.AsyncHTTPTransport()
    auth = _Auth(
        oidc_config=oidc_config,
        credentials=wvc.init.Auth.bearer_token(
            access_token="Doesn't matter", refresh_token="Doesn't matter"
        ),
        make_mounts=lambda: {"http://": transport},
        trust_env=False,
        colour="async",
    )
    auth._token_endpoint = "http://localhost:1234/token"  # so that no request is made

    async with await _Auth.aresult(auth.get_auth_session()) as session:
        assert session.trust_env is False
        assert list(session._mounts.values()) == [transport]

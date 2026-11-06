from typing import Any, Dict, List, Union

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC


@pytest.fixture
def revoke_requests(weaviate_mock: HTTPServer) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []

    def handler(request: Request) -> Response:
        requests.append(request.get_json())
        return Response(status=200)

    weaviate_mock.expect_request(
        "/v1/authz/users/alice/revoke", method="POST"
    ).respond_with_handler(handler)
    return requests


@pytest.mark.parametrize("role_names", ["reader", ["reader"]])
@pytest.mark.parametrize(
    ("user_type", "expected_body"),
    [
        ("db", {"roles": ["reader"], "userType": "db"}),
        ("oidc", {"roles": ["reader"], "userType": "oidc"}),
    ],
)
def test_revoke_roles_user_type(
    weaviate_client: weaviate.WeaviateClient,
    revoke_requests: List[Dict[str, Any]],
    user_type: str,
    role_names: Union[str, List[str]],
    expected_body: Dict[str, Any],
) -> None:
    getattr(weaviate_client.users, user_type).revoke_roles(user_id="alice", role_names=role_names)

    assert revoke_requests == [expected_body]


@pytest.mark.asyncio
@pytest.mark.parametrize("role_names", ["reader", ["reader"]])
@pytest.mark.parametrize(
    ("user_type", "expected_body"),
    [
        ("db", {"roles": ["reader"], "userType": "db"}),
        ("oidc", {"roles": ["reader"], "userType": "oidc"}),
    ],
)
async def test_revoke_roles_user_type_async(
    revoke_requests: List[Dict[str, Any]],
    user_type: str,
    role_names: Union[str, List[str]],
    expected_body: Dict[str, Any],
) -> None:
    async with weaviate.use_async_with_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    ) as client:
        await getattr(client.users, user_type).revoke_roles(user_id="alice", role_names=role_names)

    assert revoke_requests == [expected_body]


@pytest.mark.parametrize("role_names", ["reader", ["reader"]])
def test_revoke_roles_deprecated(
    weaviate_client: weaviate.WeaviateClient,
    revoke_requests: List[Dict[str, Any]],
    role_names: Union[str, List[str]],
) -> None:
    with pytest.warns(DeprecationWarning, match="users.db.revoke_roles"):
        weaviate_client.users.revoke_roles(user_id="alice", role_names=role_names)

    assert revoke_requests == [{"roles": ["reader"]}]


@pytest.mark.asyncio
@pytest.mark.parametrize("role_names", ["reader", ["reader"]])
async def test_revoke_roles_deprecated_async(
    revoke_requests: List[Dict[str, Any]], role_names: Union[str, List[str]]
) -> None:
    async with weaviate.use_async_with_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    ) as client:
        with pytest.warns(DeprecationWarning, match="users.db.revoke_roles"):
            await client.users.revoke_roles(user_id="alice", role_names=role_names)

    assert revoke_requests == [{"roles": ["reader"]}]

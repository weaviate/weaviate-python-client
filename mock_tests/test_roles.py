import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

import weaviate
from weaviate.classes.rbac import Permissions


@pytest.mark.parametrize(
    "status, body, expected",
    [(200, "true", True), (200, "false", False), (404, "{}", False)],
)
def test_has_permissions(
    weaviate_mock: HTTPServer,
    weaviate_client: weaviate.WeaviateClient,
    status: int,
    body: str,
    expected: bool,
) -> None:
    weaviate_mock.expect_request(
        "/v1/authz/roles/reader/has-permission", method="POST"
    ).respond_with_response(Response(body, status=status, content_type="application/json"))
    permissions = Permissions.collections(collection="Books", read_config=True)
    assert weaviate_client.roles.has_permissions(permissions=permissions, role="reader") is expected

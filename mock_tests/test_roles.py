import pytest
from pytest_httpserver import HTTPServer

import weaviate
from weaviate.classes.rbac import Permissions


@pytest.mark.parametrize("answer", [True, False])
def test_has_permissions(
    weaviate_mock: HTTPServer, weaviate_client: weaviate.WeaviateClient, answer: bool
) -> None:
    weaviate_mock.expect_request(
        "/v1/authz/roles/reader/has-permission", method="POST"
    ).respond_with_json(answer)
    permissions = Permissions.collections(collection="Books", read_config=True)
    assert weaviate_client.roles.has_permissions(permissions=permissions, role="reader") is answer

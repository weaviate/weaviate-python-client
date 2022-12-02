import json
from typing import Dict

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate


@pytest.mark.parametrize(
    "header",
    [
        {},
        {"Authorization": "Bearer test"},
        {"Authorization": "Bearer test", "SomethingElse": "Value"},
    ],
)
def test_additional_headers(weaviate_mock, header: Dict[str, str]):
    """Test that client sends given headers."""

    def handler(request: Request):
        assert request.headers["content-type"] == "application/json"
        for key, val in header.items():
            assert request.headers[key] == val
        return Response(json.dumps({}))

    weaviate_mock.expect_request("/v1/schema").respond_with_handler(handler)

    client = weaviate.Client(url="http://127.0.0.1:23534", additional_headers=header)
    client.schema.delete_all()  # some call that includes headers


@pytest.mark.parametrize("version,warning", [("1.13", True), ("1.14", False)])
def test_warning_old_weaviate(recwarn, httpserver: HTTPServer, version: str, warning: bool):
    """Test that we warn if a new client version is using an old weaviate server."""
    httpserver.expect_request("/v1/meta").respond_with_json({"version": version})
    weaviate.Client(url="http://127.0.0.1:23534")

    if warning:
        assert len(recwarn) == 1
        w = recwarn.pop()
        assert issubclass(w.category, DeprecationWarning)
        assert str(w.message).startswith("Dep001")
    else:
        assert len(recwarn) == 0

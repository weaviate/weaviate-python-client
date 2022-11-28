import json
from typing import Dict

import pytest
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

    # weaviate_mock.expect_request("/v1/schema", headers={"Authorization":"dfsdf"}).respond_with_json({})

    def handler(request: Request):
        assert request.headers["content-type"] == "application/json"
        for key, val in header.items():
            assert request.headers[key] == val
        return Response(json.dumps({}))

    weaviate_mock.expect_request("/v1/schema").respond_with_handler(handler)

    client = weaviate.Client(url="http://127.0.0.1:23534", additional_headers=header)
    client.schema.delete_all()  # some call that includes headers

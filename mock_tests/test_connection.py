import json
import time
from typing import Dict

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL, MOCK_IP, MOCK_PORT


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

    client = weaviate.Client(MOCK_SERVER_URL, additional_headers=header)
    client.schema.delete_all()  # some call that includes headers


@pytest.mark.parametrize("version,warning", [("1.13", True), ("1.14", False)])
def test_warning_old_weaviate(recwarn, ready_mock: HTTPServer, version: str, warning: bool):
    """Test that we warn if a new client version is using an old weaviate server."""
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": version})
    weaviate.Client(MOCK_SERVER_URL)

    if warning:
        assert any(str(w.message).startswith("Dep001") for w in recwarn)
        assert any(str(w.message).startswith("Dep004") for w in recwarn)
    else:
        assert any(str(w.message).startswith("Dep004") for w in recwarn)


def test_wait_for_weaviate(httpserver: HTTPServer):
    def handler(request: Request):
        time.sleep(0.01)
        return Response(json.dumps({}))

    def handler_meta(request: Request):
        assert time.time() > start_time - 1
        return Response(json.dumps({"version": "1.16"}))

    httpserver.expect_request("/v1/meta").respond_with_handler(handler_meta)
    httpserver.expect_request("/v1/.well-known/ready").respond_with_handler(handler)
    start_time = time.time()
    weaviate.Client(MOCK_SERVER_URL, startup_period=30)


def test_user_pw_in_url(weaviate_mock):
    """Test that user and pw can be in the url."""
    weaviate.Client("http://user:pw@" + MOCK_IP + ":" + str(MOCK_PORT))  # no exception

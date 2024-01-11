import time

import pytest
from requests import ReadTimeout
from werkzeug.wrappers import Request, Response

import weaviate
from mock_tests.conftest import MOCK_SERVER_URL


def test_schema_timeout_error(weaviate_mock):
    """Tests that expected timeout exception is raised."""

    def handler(request: Request):
        time.sleep(1.5)  # cause timeout
        return Response(status=200)

    weaviate_mock.expect_request("/v1/schema/Test").respond_with_handler(handler)
    client = weaviate.Client(MOCK_SERVER_URL, timeout_config=(1, 1))

    with pytest.raises(ReadTimeout):
        client.schema.exists("Test")


def test_schema_unknown_status_code(weaviate_mock):
    """Tests that expected UnexpectedStatusCodeException exception is raised."""

    def handler(request: Request):
        return Response(status=403)

    weaviate_mock.expect_request("/v1/schema/Test").respond_with_handler(handler)
    client = weaviate.Client(MOCK_SERVER_URL)

    with pytest.raises(weaviate.UnexpectedStatusCodeException):
        client.schema.exists("Test")


def test_schema_exists(weaviate_mock):
    """Tests correct behaviour."""

    def handler(request: Request, status: int):
        return Response(status=status)

    weaviate_mock.expect_request("/v1/schema/Exists").respond_with_handler(
        lambda r: handler(r, 200)
    )
    weaviate_mock.expect_request("/v1/schema/DoesNotExists").respond_with_handler(
        lambda r: handler(r, 404)
    )
    client = weaviate.Client(MOCK_SERVER_URL)

    assert client.schema.exists("Exists") is True
    assert client.schema.exists("DoesNotExists") is False

    assert client.schema.exists("exists") is True
    assert client.schema.exists("doesNotExists") is False

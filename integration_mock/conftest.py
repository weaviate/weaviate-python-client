import pytest
from pytest_httpserver import HTTPServer


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return "127.0.0.1", 23534


@pytest.fixture(scope="function")
def weaviate_mock(httpserver: HTTPServer):
    httpserver.expect_request("/v1/meta").respond_with_json({"version": "1.16"})
    yield httpserver

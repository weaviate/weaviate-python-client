import random

import pytest
from pytest_httpserver import HTTPServer

MOCK_IP = "127.0.0.1"
MOCK_PORT = random.randint(20000, 25000)
CLIENT_ID = "DoesNotMatter"
MOCK_SERVER_URL = "http://" + MOCK_IP + ":" + str(MOCK_PORT)


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return MOCK_IP, MOCK_PORT


@pytest.fixture(scope="function")
def weaviate_mock(httpserver: HTTPServer):
    httpserver.expect_request("/v1/meta").respond_with_json({"version": "1.16"})
    yield httpserver


@pytest.fixture(scope="function")
def weaviate_auth_mock(weaviate_mock):
    weaviate_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_json(
        {"href": MOCK_SERVER_URL + "/endpoints", "clientId": CLIENT_ID}
    )
    weaviate_mock.expect_request("/endpoints").respond_with_json(
        {"token_endpoint": MOCK_SERVER_URL + "/auth"}
    )
    yield weaviate_mock

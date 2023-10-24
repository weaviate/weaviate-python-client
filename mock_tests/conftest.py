import json

import pytest
from pytest_httpserver import HTTPServer, HeaderValueMatcher
from werkzeug.wrappers import Response

from weaviate.connect.connection import ConnectionParams, ProtocolParams

MOCK_IP = "127.0.0.1"
MOCK_PORT = 23536
CLIENT_ID = "DoesNotMatter"
MOCK_SERVER_URL = "http://" + MOCK_IP + ":" + str(MOCK_PORT)
MOCK_SERVER_CONNECTION_PARAMS = ConnectionParams(
    http=ProtocolParams(host=MOCK_IP, port=MOCK_PORT, secure=False)
)

# pytest_httpserver 'Authorization' HeaderValueMatcher does not work with Bearer tokens.
# Hence, overwrite it with the default header value matcher that just compares for equality.
HeaderValueMatcher.DEFAULT_MATCHERS[
    "Authorization"
] = HeaderValueMatcher.default_header_value_matcher


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return MOCK_IP, MOCK_PORT


@pytest.fixture(scope="function")
def ready_mock(httpserver: HTTPServer):
    httpserver.expect_request("/v1/.well-known/ready").respond_with_json({})
    yield httpserver


@pytest.fixture(scope="function")
def weaviate_mock(ready_mock):
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.16"})
    ready_mock.expect_request("/v1/nodes").respond_with_json({"nodes": [{"gitHash": "ABC"}]})

    yield ready_mock


@pytest.fixture(scope="function")
def weaviate_no_auth_mock(ready_mock):
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.16"})
    ready_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_response(
        Response(json.dumps({}), status=404)
    )

    yield ready_mock


@pytest.fixture(scope="function")
def weaviate_auth_mock(weaviate_mock):
    weaviate_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_json(
        {
            "href": MOCK_SERVER_URL + "/endpoints",
            "clientId": CLIENT_ID,
        }
    )
    weaviate_mock.expect_request("/endpoints").respond_with_json(
        {"token_endpoint": MOCK_SERVER_URL + "/auth"}
    )
    yield weaviate_mock

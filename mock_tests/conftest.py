import json

import pytest
from pytest_httpserver import HTTPServer, HeaderValueMatcher
from werkzeug.wrappers import Response

from weaviate.connect.base import ConnectionParams, ProtocolParams

from concurrent import futures
from grpc import ServicerContext
import grpc

from grpc_health.v1.health_pb2 import HealthCheckResponse, HealthCheckRequest
from grpc_health.v1.health_pb2_grpc import HealthServicer, add_HealthServicer_to_server

MOCK_IP = "127.0.0.1"
MOCK_PORT = 23536
MOCK_PORT_GRPC = 23537

CLIENT_ID = "DoesNotMatter"
MOCK_SERVER_URL = "http://" + MOCK_IP + ":" + str(MOCK_PORT)
# only http endpoint is tested, grpc port doesnt matter but needs to be supplied
MOCK_SERVER_CONNECTION_PARAMS = ConnectionParams(
    http=ProtocolParams(host=MOCK_IP, port=MOCK_PORT, secure=False),
    grpc=ProtocolParams(host=MOCK_IP, port=MOCK_PORT + 1, secure=False),
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
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.24"})
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


# Implement the health check service
class MockHealthServicer(HealthServicer):
    def Check(self, request: HealthCheckRequest, context: ServicerContext) -> HealthCheckResponse:
        return HealthCheckResponse(status=HealthCheckResponse.SERVING)


@pytest.fixture(scope="module")
def start_grpc_server() -> grpc.Server:
    # Create a gRPC server
    server: grpc.Server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add the health check service to the server
    add_HealthServicer_to_server(MockHealthServicer(), server)

    # Listen on a specific port
    server.add_insecure_port(f"[::]:{MOCK_PORT_GRPC}")
    server.start()

    yield server

    # Teardown - stop the server
    server.stop(0)

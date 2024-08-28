import json
import ssl
from concurrent import futures

import grpc
import pytest
import trustme
from grpc_health.v1.health_pb2_grpc import add_HealthServicer_to_server
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Response

import weaviate
from mock_tests.conftest import MockHealthServicer, MOCK_IP, MOCK_PORT_GRPC

SERVER = "127.0.0.1"
PORT = 8888
MOCK_PORT_GRPC_SSL = 50053


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return SERVER, PORT


@pytest.fixture(scope="session")
def httpserver_ssl_context():
    ca = trustme.CA()
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_cert = ca.issue_cert(SERVER)
    server_cert.configure_cert(server_context)

    return server_context


@pytest.fixture(scope="module")
def start_grpc_server_ssl() -> grpc.Server:
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add the health check service to the server
    add_HealthServicer_to_server(MockHealthServicer(), server)

    # Create server credentials using the SSL context
    ca = trustme.CA()
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_cert = ca.issue_cert(SERVER)
    server_cert.configure_cert(server_context)
    server_credentials = grpc.ssl_server_credentials(
        [(server_cert.private_key_pem.bytes(), server_cert.cert_chain_pems[0].bytes())]
    )

    # Listen on a specific port with SSL
    server.add_secure_port(f"[::]:{MOCK_PORT_GRPC_SSL}", server_credentials)
    server.start()

    yield server

    # Teardown - stop the server
    server.stop(0)


def test_disable_ssl_verification(
    httpserver: HTTPServer, start_grpc_server_ssl: grpc.Server, start_grpc_server: grpc.Server
):
    httpserver.expect_request("/v1/.well-known/ready").respond_with_json({})
    httpserver.expect_request("/v1/meta").respond_with_json({"version": "1.24"})
    httpserver.expect_request("/v1/nodes").respond_with_json({"nodes": [{"gitHash": "ABC"}]})
    httpserver.expect_request("/v1/.well-known/openid-configuration").respond_with_response(
        Response(json.dumps({}), status=404)
    )

    assert httpserver.port == PORT
    assert httpserver.host == SERVER

    # test http connection with ssl
    with pytest.raises(weaviate.exceptions.WeaviateConnectionError):
        weaviate.connect_to_custom(
            http_port=PORT,
            http_host=SERVER,
            grpc_port=MOCK_PORT_GRPC,
            http_secure=True,
            grpc_host=MOCK_IP,
            grpc_secure=False,
        )

    # test grpc connection with ssl
    with pytest.raises(weaviate.exceptions.WeaviateConnectionError):
        weaviate.connect_to_custom(
            http_port=PORT,
            http_host=SERVER,
            grpc_port=MOCK_PORT_GRPC_SSL,
            http_secure=True,
            grpc_host=SERVER,
            grpc_secure=True,
        )

    # test http connection with ssl and verify disabled
    weaviate.connect_to_custom(
        http_port=PORT,
        http_host=SERVER,
        grpc_port=MOCK_PORT_GRPC,
        http_secure=True,
        grpc_host=MOCK_IP,
        grpc_secure=False,
        additional_config=weaviate.config.AdditionalConfig(disable_ssl_verification=True),
    )

    # test grpc connection with ssl and verify disabled
    weaviate.connect_to_custom(
        http_port=PORT,
        http_host=SERVER,
        grpc_port=MOCK_PORT_GRPC_SSL,
        http_secure=True,
        grpc_host=SERVER,
        grpc_secure=True,
        additional_config=weaviate.config.AdditionalConfig(disable_ssl_verification=True),
    )

    httpserver.check_assertions()

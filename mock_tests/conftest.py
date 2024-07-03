import json
from concurrent import futures
from typing import Generator, Mapping

import grpc
import pytest
from grpc import ServicerContext
from grpc_health.v1.health_pb2 import HealthCheckResponse, HealthCheckRequest
from grpc_health.v1.health_pb2_grpc import HealthServicer, add_HealthServicer_to_server
from pytest_httpserver import HTTPServer, HeaderValueMatcher
from werkzeug.wrappers import Response

import weaviate
from weaviate.connect.base import ConnectionParams, ProtocolParams
from weaviate.proto.v1 import properties_pb2, tenants_pb2, search_get_pb2, weaviate_pb2_grpc

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
def weaviate_mock(ready_mock: HTTPServer):
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": "1.25"})
    ready_mock.expect_request("/v1/nodes").respond_with_json({"nodes": [{"gitHash": "ABC"}]})

    yield ready_mock


@pytest.fixture(scope="function")
def weaviate_no_auth_mock(weaviate_mock: HTTPServer):
    weaviate_mock.expect_request("/v1/meta").respond_with_json({"version": "1.25"})
    weaviate_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_response(
        Response(json.dumps({}), status=404)
    )

    yield weaviate_mock


@pytest.fixture(scope="function")
def weaviate_auth_mock(weaviate_mock: HTTPServer):
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


@pytest.fixture(scope="function")
def start_grpc_server() -> Generator[grpc.Server, None, None]:
    # Create a gRPC server
    server: grpc.Server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Implement the health check service
    class MockHealthServicer(HealthServicer):
        def Check(
            self, request: HealthCheckRequest, context: ServicerContext
        ) -> HealthCheckResponse:
            return HealthCheckResponse(status=HealthCheckResponse.SERVING)

    # Add the health check service to the server
    add_HealthServicer_to_server(MockHealthServicer(), server)

    # Listen on a specific port
    server.add_insecure_port(f"[::]:{MOCK_PORT_GRPC}")
    server.start()

    yield server

    # Teardown - stop the server
    server.stop(0)


@pytest.fixture(scope="function")
def weaviate_client(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    yield client
    client.close()


@pytest.fixture(scope="function")
def tenants_collection(
    weaviate_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> weaviate.collections.Collection:
    class MockWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
        def TenantsGet(
            self, request: tenants_pb2.TenantsGetRequest, context: ServicerContext
        ) -> tenants_pb2.TenantsGetReply:
            return tenants_pb2.TenantsGetReply(
                tenants=[
                    tenants_pb2.Tenant(
                        name="tenant1", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_HOT
                    ),
                    tenants_pb2.Tenant(
                        name="tenant2", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_COLD
                    ),
                    tenants_pb2.Tenant(
                        name="tenant3", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_FROZEN
                    ),
                    tenants_pb2.Tenant(
                        name="tenant4", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_FREEZING
                    ),
                    tenants_pb2.Tenant(
                        name="tenant5",
                        activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_UNFREEZING,
                    ),
                    tenants_pb2.Tenant(
                        name="tenant6", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_UNFROZEN
                    ),
                ]
            )

    weaviate_pb2_grpc.add_WeaviateServicer_to_server(MockWeaviateService(), start_grpc_server)
    return weaviate_client.collections.get("TenantsGetCollectionName")


@pytest.fixture(scope="function")
def year_zero_collection(
    weaviate_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> weaviate.collections.Collection:
    class MockWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
        def Search(
            self, request: search_get_pb2.SearchRequest, context: grpc.ServicerContext
        ) -> search_get_pb2.SearchReply:
            zero_date: properties_pb2.Value.date_value = properties_pb2.Value(
                date_value="0000-01-30T00:00:00Z"
            )
            date_prop: Mapping[str, properties_pb2.Value.date_value] = {"date": zero_date}
            return search_get_pb2.SearchReply(
                results=[
                    search_get_pb2.SearchResult(
                        properties=search_get_pb2.PropertiesResult(
                            non_ref_props=properties_pb2.Properties(fields=date_prop)
                        )
                    ),
                ]
            )

    weaviate_pb2_grpc.add_WeaviateServicer_to_server(MockWeaviateService(), start_grpc_server)
    return weaviate_client.collections.get("YearZeroCollection")

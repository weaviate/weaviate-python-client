import json
import time
from concurrent import futures
from typing import Generator, Mapping

import grpc
import pytest
from grpc import ServicerContext
from grpc_health.v1.health_pb2 import HealthCheckResponse, HealthCheckRequest
from grpc_health.v1.health_pb2_grpc import HealthServicer, add_HealthServicer_to_server
from pytest_httpserver import HTTPServer, HeaderValueMatcher
from werkzeug.wrappers import Request, Response

import weaviate
from weaviate.connect.base import ConnectionParams, ProtocolParams
from weaviate.proto.v1 import (
    batch_pb2,
    properties_pb2,
    tenants_pb2,
    search_get_pb2,
    weaviate_pb2_grpc,
)

from mock_tests.mock_data import mock_class

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
HeaderValueMatcher.DEFAULT_MATCHERS["Authorization"] = (
    HeaderValueMatcher.default_header_value_matcher
)


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
def weaviate_timeouts_mock(weaviate_no_auth_mock: HTTPServer):
    def slow_get(request: Request) -> Response:
        time.sleep(1)
        return Response(json.dumps({"doesn't": "matter"}), content_type="application/json")

    def slow_post(request: Request) -> Response:
        time.sleep(2)
        return Response(json.dumps({"doesn't": "matter"}), content_type="application/json")

    weaviate_no_auth_mock.expect_request(
        f"/v1/schema/{mock_class['class']}", method="GET"
    ).respond_with_handler(slow_get)
    weaviate_no_auth_mock.expect_request("/v1/objects", method="POST").respond_with_handler(
        slow_post
    )

    yield weaviate_no_auth_mock


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
def weaviate_timeouts_client(
    weaviate_timeouts_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        additional_config=weaviate.classes.init.AdditionalConfig(
            timeout=weaviate.classes.init.Timeout(query=0.5, insert=1.5)
        ),
    )
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
                        name="tenant6", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_ACTIVE
                    ),
                    tenants_pb2.Tenant(
                        name="tenant7", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_INACTIVE
                    ),
                    tenants_pb2.Tenant(
                        name="tenant8", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_OFFLOADED
                    ),
                    tenants_pb2.Tenant(
                        name="tenant9",
                        activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_OFFLOADING,
                    ),
                    tenants_pb2.Tenant(
                        name="tenant10",
                        activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_ONLOADING,
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


@pytest.fixture(scope="function")
def timeouts_collection(
    weaviate_timeouts_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> weaviate.collections.Collection:
    class MockWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
        def Search(
            self, request: search_get_pb2.SearchRequest, context: grpc.ServicerContext
        ) -> search_get_pb2.SearchReply:
            time.sleep(1)
            return search_get_pb2.SearchReply()

        def BatchObjects(
            self, request: batch_pb2.BatchObjectsRequest, context: grpc.ServicerContext
        ) -> batch_pb2.BatchObjectsReply:
            time.sleep(2)
            return batch_pb2.BatchObjectsReply()

    weaviate_pb2_grpc.add_WeaviateServicer_to_server(MockWeaviateService(), start_grpc_server)
    return weaviate_timeouts_client.collections.get(mock_class["class"])


class MockRetriesWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
    search_count = 0
    tenants_count = 0

    def Search(
        self, request: search_get_pb2.SearchRequest, context: grpc.ServicerContext
    ) -> search_get_pb2.SearchReply:
        if self.search_count == 0:
            self.search_count += 1
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return search_get_pb2.SearchReply()
        if self.search_count == 1:
            self.search_count += 1
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Service is unavailable")
            return search_get_pb2.SearchReply()
        return search_get_pb2.SearchReply(
            results=[
                search_get_pb2.SearchResult(
                    properties=search_get_pb2.PropertiesResult(
                        non_ref_props=properties_pb2.Properties(
                            fields={"name": properties_pb2.Value(text_value="test")}
                        )
                    )
                )
            ]
        )

    def TenantsGet(
        self, request: tenants_pb2.TenantsGetRequest, context: ServicerContext
    ) -> tenants_pb2.TenantsGetReply:
        if self.tenants_count == 0:
            self.tenants_count += 1
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return tenants_pb2.TenantsGetReply()
        if self.tenants_count == 1:
            self.tenants_count += 1
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("Service is unavailable")
            return tenants_pb2.TenantsGetReply()
        return tenants_pb2.TenantsGetReply(
            tenants=[
                tenants_pb2.Tenant(
                    name="tenant1", activity_status=tenants_pb2.TENANT_ACTIVITY_STATUS_ACTIVE
                )
            ]
        )


@pytest.fixture(scope="function")
def retries(
    weaviate_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
) -> tuple[weaviate.collections.Collection, MockRetriesWeaviateService]:
    service = MockRetriesWeaviateService()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return weaviate_client.collections.get("RetriesCollection"), service

import grpc
from pytest_httpserver import HTTPServer

import weaviate
from weaviate.classes.tenants import TenantActivityStatus

from .conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC


def test_tenants_get(weaviate_mock: HTTPServer, start_grpc_server: grpc.Server) -> None:
    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    collection = client.collections.get("Doesn'tMatter")
    tenants = list(collection.tenants.get().values())
    assert len(tenants) == 6

    assert tenants[0].name == "tenant1"
    assert tenants[0].activity_status == TenantActivityStatus.HOT

    assert tenants[1].name == "tenant2"
    assert tenants[1].activity_status == TenantActivityStatus.COLD

    assert tenants[2].name == "tenant3"
    assert tenants[2].activity_status == TenantActivityStatus.FROZEN

    assert tenants[3].name == "tenant4"
    assert tenants[3].activity_status == TenantActivityStatus.FREEZING

    assert tenants[4].name == "tenant5"
    assert tenants[4].activity_status == TenantActivityStatus.UNFREEZING

    assert tenants[5].name == "tenant6"
    assert tenants[5].activity_status == TenantActivityStatus.UNFROZEN

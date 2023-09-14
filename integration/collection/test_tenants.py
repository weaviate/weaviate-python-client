from weaviate.collection.classes.config import (
    ConfigFactory,
    VectorizerFactory,
)
from weaviate.collection.classes.tenants import Tenant, TenantActivityStatus

from .conftest import CollectionObjectFactory


def test_tenants(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="Tenants",
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(
            enabled=True,
        ),
    )

    collection.tenants.add([Tenant(name="tenant1")])

    tenants = collection.tenants.get()
    assert len(tenants) == 1
    assert type(tenants["tenant1"]) is Tenant
    assert tenants["tenant1"].name == "tenant1"

    collection.tenants.remove(["tenant1"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0


def test_tenant_with_activity(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestTenantActivity",
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )
    collection.tenants.add(
        [
            Tenant(name="1", activity_status=TenantActivityStatus.HOT),
            Tenant(name="2", activity_status=TenantActivityStatus.COLD),
            Tenant(name="3"),
        ]
    )
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT
    assert tenants["2"].activity_status == TenantActivityStatus.COLD
    assert tenants["3"].activity_status == TenantActivityStatus.HOT


def test_update_tenant(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestUpdateTenant",
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )
    collection.tenants.add([Tenant(name="1", activity_status=TenantActivityStatus.HOT)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT

    collection.tenants.update([Tenant(name="1", activity_status=TenantActivityStatus.COLD)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.COLD

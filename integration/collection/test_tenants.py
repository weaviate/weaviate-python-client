from weaviate.collection import Collection
from weaviate.collection.classes.config import (
    ConfigFactory,
    VectorizerFactory,
)
from weaviate.collection.classes.tenants import Tenant, TenantActivityStatus


def test_tenants(collection_basic: Collection):
    collection = collection_basic.create(
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

    collection_basic.delete("Tenants")


def test_tenant_with_activity(collection_basic: Collection):
    name = "TestTenantActivity"
    collection = collection_basic.create(
        name=name,
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


def test_update_tenant(collection_basic: Collection):
    name = "TestUpdateTenant"
    collection = collection_basic.create(
        name=name,
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )
    collection.tenants.add([Tenant(name="1", activity_status=TenantActivityStatus.HOT)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT

    collection.tenants.update([Tenant(name="1", activity_status=TenantActivityStatus.COLD)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.COLD

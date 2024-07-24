import weaviate
from weaviate.classes.tenants import TenantActivityStatus


def test_tenants_get(tenants_collection: weaviate.collections.Collection) -> None:
    tenants = list(tenants_collection.tenants.get().values())
    assert len(tenants) == 10

    assert tenants[0].name == "tenant1"
    assert tenants[0].activity_status == TenantActivityStatus.ACTIVE

    assert tenants[1].name == "tenant2"
    assert tenants[1].activity_status == TenantActivityStatus.INACTIVE

    assert tenants[2].name == "tenant3"
    assert tenants[2].activity_status == TenantActivityStatus.OFFLOADED

    assert tenants[3].name == "tenant4"
    assert tenants[3].activity_status == TenantActivityStatus.OFFLOADING

    assert tenants[4].name == "tenant5"
    assert tenants[4].activity_status == TenantActivityStatus.ONLOADING

    assert tenants[5].name == "tenant6"
    assert tenants[5].activity_status == TenantActivityStatus.ACTIVE

    assert tenants[6].name == "tenant7"
    assert tenants[6].activity_status == TenantActivityStatus.INACTIVE

    assert tenants[7].name == "tenant8"
    assert tenants[7].activity_status == TenantActivityStatus.OFFLOADED

    assert tenants[8].name == "tenant9"
    assert tenants[8].activity_status == TenantActivityStatus.OFFLOADING

    assert tenants[9].name == "tenant10"
    assert tenants[9].activity_status == TenantActivityStatus.ONLOADING

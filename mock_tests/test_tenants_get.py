import weaviate
from weaviate.classes.tenants import TenantActivityStatus


def test_tenants_get(tenants_collection: weaviate.collections.Collection) -> None:
    tenants = list(tenants_collection.tenants.get().values())
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

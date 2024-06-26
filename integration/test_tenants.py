import pytest
import uuid
from typing import List, Union

from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    Reconfigure,
)
from weaviate.collections.classes.data import (
    DataObject,
)
from weaviate.collections.classes.tenants import Tenant, TenantActivityStatus
from weaviate.exceptions import WeaviateUnsupportedFeatureError


def test_delete_by_id_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create(Tenant(name="tenant1"))
    tenant1 = collection.with_tenant("tenant1")
    uuid = tenant1.data.insert(properties={})
    assert tenant1.query.fetch_object_by_id(uuid) is not None
    assert tenant1.data.delete_by_id(uuid)
    assert tenant1.query.fetch_object_by_id(uuid) is None


def test_insert_many_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    ret = tenant1.data.insert_many(
        [
            DataObject(properties={"name": "some name"}, vector=[1, 2, 3]),
            DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
        ]
    )
    assert not ret.has_errors
    obj1 = tenant1.query.fetch_object_by_id(ret.uuids[0])
    obj2 = tenant1.query.fetch_object_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"
    assert tenant2.query.fetch_object_by_id(ret.uuids[0]) is None
    assert tenant2.query.fetch_object_by_id(ret.uuids[1]) is None


def test_replace_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(properties={"name": "some name"})
    tenant1.data.replace(properties={"name": "other name"}, uuid=uuid)
    assert tenant1.query.fetch_object_by_id(uuid).properties["name"] == "other name"
    assert tenant2.query.fetch_object_by_id(uuid) is None


def test_tenants_update(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.update(properties={"name": "other name"}, uuid=uuid, vector=[1, 2, 3])
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "other name"
    assert obj.vector["default"] == [1, 2, 3]


def test_update_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(properties={"name": "some name"})
    tenant1.data.update(properties={"name": "other name"}, uuid=uuid)
    assert tenant1.query.fetch_object_by_id(uuid).properties["name"] == "other name"
    assert tenant2.query.fetch_object_by_id(uuid) is None


def test_tenants(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])

    tenants = collection.tenants.get()
    assert len(tenants) == 2
    assert type(tenants["tenant1"]) is Tenant
    assert type(tenants["tenant2"]) is Tenant
    assert tenants["tenant1"].name == "tenant1"
    assert tenants["tenant2"].name == "tenant2"

    if collection._connection._weaviate_version.supports_tenants_get_grpc:
        tenants = collection.tenants.get_by_names(tenants=["tenant2"])
        assert len(tenants) == 1
        assert type(tenants["tenant2"]) is Tenant
        assert tenants["tenant2"].name == "tenant2"
    else:
        pytest.raises(
            WeaviateUnsupportedFeatureError, collection.tenants.get_by_names, tenants=["tenant2"]
        )

    collection.tenants.remove(["tenant1", "tenant2"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0


def test_search_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert({"name": "some name"})
    objects1 = tenant1.query.bm25(query="some").objects
    assert len(objects1) == 1
    assert objects1[0].uuid == uuid1

    objects2 = tenant2.query.bm25(query="some").objects
    assert len(objects2) == 0


def test_fetch_object_by_id_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")

    uuid1 = tenant1.data.insert({"name": "some name"})
    obj1 = tenant1.query.fetch_object_by_id(uuid1)
    assert obj1.properties["name"] == "some name"

    obj2 = tenant2.query.fetch_object_by_id(uuid1)
    assert obj2 is None

    uuid2 = tenant2.data.insert({"name": "some other name"})
    obj3 = tenant2.query.fetch_object_by_id(uuid2)
    assert obj3.properties["name"] == "some other name"

    obj4 = tenant1.query.fetch_object_by_id(uuid2)
    assert obj4 is None


def test_fetch_objects_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")

    tenant1.data.insert({"name": "some name"})
    objects = tenant1.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "some name"

    objects = tenant2.query.fetch_objects().objects
    assert len(objects) == 0

    tenant2.data.insert({"name": "some other name"})
    objects = tenant2.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "some other name"


def test_exist_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])

    uuid1 = collection.with_tenant("Tenant1").data.insert({})
    uuid2 = collection.with_tenant("Tenant2").data.insert({})

    assert collection.with_tenant("Tenant1").data.exists(uuid1)
    assert not collection.with_tenant("Tenant2").data.exists(uuid1)
    assert collection.with_tenant("Tenant2").data.exists(uuid2)
    assert not collection.with_tenant("Tenant1").data.exists(uuid2)


def test_tenant_with_activity(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create(
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


def test_update_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create(Tenant(name="1", activity_status=TenantActivityStatus.HOT))
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT

    collection.tenants.update(Tenant(name="1", activity_status=TenantActivityStatus.COLD))
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.COLD


def test_tenant_exists(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    tenant = Tenant(name="1")
    collection.tenants.create([tenant])

    if collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        with pytest.raises(WeaviateUnsupportedFeatureError):
            collection.tenants.exists(tenant.name)
    else:
        assert collection.tenants.exists(tenant.name)
        assert collection.tenants.exists(tenant)
        assert not collection.tenants.exists("2")


@pytest.mark.parametrize("tenant1", ["tenant1", Tenant(name="tenant1")])
@pytest.mark.parametrize("tenant2", ["tenant2", Tenant(name="tenant2")])
@pytest.mark.parametrize("tenant3", ["tenant3", Tenant(name="tenant3")])
def test_tenant_get_by_name(
    collection_factory: CollectionFactory,
    tenant1: Union[str, Tenant],
    tenant2: Union[str, Tenant],
    tenant3: Union[str, Tenant],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )

    collection.tenants.create([Tenant(name="tenant1")])

    if collection._connection._weaviate_version.supports_tenants_get_grpc:
        tenant = collection.tenants.get_by_name(tenant1)
        assert tenant is not None
        assert tenant.name == "tenant1"

        tenant = collection.tenants.get_by_name(tenant2)
        assert tenant is None
    else:
        pytest.raises(WeaviateUnsupportedFeatureError, collection.tenants.get_by_name, tenant3)


def test_autotenant_toggling(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    if collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        return

    assert not collection.config.get().multi_tenancy_config.auto_tenant_creation

    collection.config.update(
        multi_tenancy_config=Reconfigure.multi_tenancy(auto_tenant_creation=True)
    )
    assert collection.config.get().multi_tenancy_config.auto_tenant_creation

    collection.config.update(
        multi_tenancy_config=Reconfigure.multi_tenancy(auto_tenant_creation=False)
    )
    assert not collection.config.get().multi_tenancy_config.auto_tenant_creation


@pytest.mark.parametrize(
    "tenants", ["tenant", Tenant(name="tenant"), ["tenant"], [Tenant(name="tenant")]]
)
def test_tenants_create(
    collection_factory: CollectionFactory, tenants: Union[str, Tenant, List[Union[str, Tenant]]]
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )

    collection.tenants.create(tenants)
    t = collection.tenants.get()
    assert len(t) == 1
    assert t["tenant"].name == "tenant"


@pytest.mark.parametrize(
    "tenants", ["tenant", Tenant(name="tenant"), ["tenant"], [Tenant(name="tenant")]]
)
def test_tenants_remove(
    collection_factory: CollectionFactory, tenants: Union[str, Tenant, List[Union[str, Tenant]]]
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )

    collection.tenants.create(["tenant", "tenantt"])
    collection.tenants.remove(tenants)
    t = collection.tenants.get()
    assert "tenant" not in t
    assert "tenantt" in t

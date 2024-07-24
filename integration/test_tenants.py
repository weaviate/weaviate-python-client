import uuid
from typing import List, Union

import pytest

from integration.conftest import ClientFactory, CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    Reconfigure,
)
from weaviate.collections.classes.data import (
    DataObject,
)
from weaviate.collections.classes.tenants import (
    Tenant,
    TenantCreate,
    TenantActivityStatus,
)
from weaviate.collections.tenants import TenantCreateInputType
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateUnsupportedFeatureError


@pytest.mark.parametrize("tenant", ["tenant1", Tenant(name="tenant1")])
def test_delete_by_id_tenant(
    collection_factory: CollectionFactory, tenant: Union[str, Tenant]
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create(tenant)
    tenant1 = collection.with_tenant(tenant)
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
    assert isinstance(tenants["tenant1"], Tenant)
    assert isinstance(tenants["tenant2"], Tenant)
    assert tenants["tenant1"].name == "tenant1"
    assert tenants["tenant2"].name == "tenant2"

    if collection._connection._weaviate_version.supports_tenants_get_grpc:
        tenants = collection.tenants.get_by_names(tenants=["tenant2"])
        assert len(tenants) == 1
        assert isinstance(tenants["tenant2"], Tenant)
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

    with pytest.warns(DeprecationWarning) as recwarn:
        collection.tenants.create(
            [
                Tenant(name="1", activity_status=TenantActivityStatus.HOT),
                Tenant(name="2", activity_status=TenantActivityStatus.COLD),
                Tenant(name="3", activity_status=TenantActivityStatus.ACTIVE),
                Tenant(name="4", activity_status=TenantActivityStatus.INACTIVE),
                Tenant(name="5"),
            ]
        )
        assert len(recwarn) == 2
        assert any("HOT is deprecated" in warn.message.args[0] for warn in recwarn.list)
        assert any("COLD is deprecated" in warn.message.args[0] for warn in recwarn.list)
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.ACTIVE
    assert tenants["2"].activity_status == TenantActivityStatus.INACTIVE
    assert tenants["3"].activity_status == TenantActivityStatus.ACTIVE
    assert tenants["4"].activity_status == TenantActivityStatus.INACTIVE
    assert tenants["5"].activity_status == TenantActivityStatus.ACTIVE


def test_update_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    with pytest.warns(DeprecationWarning) as recwarn:
        collection.tenants.create(Tenant(name="1", activity_status=TenantActivityStatus.HOT))
        assert len(recwarn) == 1
        assert any("HOT is deprecated" in warn.message.args[0] for warn in recwarn.list)
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.ACTIVE

    with pytest.warns(DeprecationWarning) as recwarn:
        collection.tenants.update(Tenant(name="1", activity_status=TenantActivityStatus.COLD))
        assert len(recwarn) == 1
        assert any("COLD is deprecated" in warn.message.args[0] for warn in recwarn.list)
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.INACTIVE

    collection.tenants.update(Tenant(name="1", activity_status=TenantActivityStatus.ACTIVE))
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.ACTIVE

    collection.tenants.update(Tenant(name="1", activity_status=TenantActivityStatus.INACTIVE))
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.INACTIVE


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
        pytest.skip("Auto-tenant creation is not supported in this version")

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
    "tenants",
    [
        "tenant",
        Tenant(name="tenant"),
        TenantCreate(name="tenant"),
        ["tenant"],
        [Tenant(name="tenant")],
        [TenantCreate(name="tenant")],
    ],
)
def test_tenants_create(
    collection_factory: CollectionFactory,
    tenants: Union[TenantCreateInputType, List[TenantCreateInputType]],
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
    "tenants",
    [
        "tenant",
        Tenant(name="tenant"),
        ["tenant"],
        [Tenant(name="tenant")],
    ],
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


@pytest.mark.parametrize(
    "tenants",
    [
        Tenant(name="1", activity_status=TenantActivityStatus.FROZEN),
        [
            Tenant(name="4", activity_status=TenantActivityStatus.FROZEN),
        ],
    ],
)
def test_tenants_create_with_read_only_activity_status(
    collection_factory: CollectionFactory, tenants: Union[Tenant, List[Tenant]]
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )
    with pytest.raises(WeaviateInvalidInputError):
        collection.tenants.create(tenants)


@pytest.mark.parametrize(
    "tenants",
    [
        Tenant(name="1", activity_status=TenantActivityStatus.OFFLOADING),
        Tenant(name="1", activity_status=TenantActivityStatus.ONLOADING),
        [
            Tenant(name="1", activity_status=TenantActivityStatus.OFFLOADING),
            Tenant(name="2", activity_status=TenantActivityStatus.ONLOADING),
        ],
    ],
)
def test_tenants_update_with_read_only_activity_status(
    collection_factory: CollectionFactory, tenants: Union[Tenant, List[Tenant]]
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )
    with pytest.raises(WeaviateInvalidInputError):
        collection.tenants.update(tenants)


def test_tenants_create_and_update_1001_tenants(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(),
    )

    tenants = [TenantCreate(name=f"tenant{i}") for i in range(1001)]

    collection.tenants.create(tenants)
    t = collection.tenants.get()
    assert len(t) == 1001
    assert all(tenant.activity_status == TenantActivityStatus.ACTIVE for tenant in t.values())

    tenants = [
        Tenant(name=f"tenant{i}", activity_status=TenantActivityStatus.INACTIVE)
        for i in range(1001)
    ]
    collection.tenants.update(tenants)
    t = collection.tenants.get()
    assert len(t) == 1001
    assert all(tenant.activity_status == TenantActivityStatus.INACTIVE for tenant in t.values())


def test_tenants_auto_tenant_creation(
    client_factory: ClientFactory, collection_factory: CollectionFactory
) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 25, 0):
        pytest.skip("Auto-tenant creation is not supported in this version")

    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(auto_tenant_creation=True),
    )

    collection.with_tenant("tenant").data.insert_many(
        [DataObject(properties={"name": "some name"}) for _ in range(101)]
    )

    client = client_factory()
    with client.batch.fixed_size(batch_size=101) as batch:
        for i in range(101):
            batch.add_object(
                collection=collection.name, properties={"name": "some name"}, tenant=f"tenant-{i}"
            )
    assert len(client.batch.failed_objects) == 0

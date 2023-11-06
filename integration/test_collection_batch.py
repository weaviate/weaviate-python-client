import uuid
import warnings
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

import pytest

import weaviate
from weaviate.collections.classes.batch import Shard
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
)
from weaviate.collections.classes.internal import FromReference
from weaviate.collections.classes.tenants import Tenant

UUID = Union[str, uuid.UUID]


@dataclass
class MockNumpyTorch:
    array: list

    def squeeze(self) -> "MockNumpyTorch":
        return self

    def tolist(self) -> list:
        return self.array


@dataclass
class MockTensorFlow:
    array: list

    def numpy(self) -> "MockNumpyTorch":
        return MockNumpyTorch(self.array)


@pytest.fixture(scope="function")
def client_sync_indexing() -> weaviate.WeaviateClient:
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    client.collections.create(
        name="Test",
        properties=[
            ReferenceProperty(name="test", target_collection="Test"),
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    yield client
    client.collections.delete_all()


@pytest.fixture(scope="function")
def client_async_indexing() -> weaviate.WeaviateClient:
    client = weaviate.connect_to_local(port=8090, grpc_port=50060)
    client.collections.delete_all()
    client.collections.create(
        name="BatchTestAsync",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
    )
    yield client
    client.collections.delete_all()


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uuid", [None, uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
def test_add_object(
    client_sync_indexing: weaviate.WeaviateClient, uuid: Optional[UUID], vector: Optional[Sequence]
):
    with client_sync_indexing.batch as batch:
        batch.add_object(
            collection="Test",
            properties={},
            uuid=uuid,
            vector=vector,
        )
        assert batch.num_objects() == 1
        assert batch.num_references() == 0
    objs = client_sync_indexing.collections.get("Test").query.fetch_objects().objects
    assert len(objs) == 1


@pytest.mark.parametrize("from_object_uuid", [uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
@pytest.mark.parametrize("to_object_uuid", [uuid.uuid4().hex, uuid.uuid4(), str(uuid.uuid4())])
@pytest.mark.parametrize("to_object_collection", [None, "Test"])
def test_add_reference(
    client_sync_indexing: weaviate.WeaviateClient,
    from_object_uuid: UUID,
    to_object_uuid: UUID,
    to_object_collection: Optional[str],
):
    """Test the `add_reference` method"""

    with client_sync_indexing.batch as batch:
        batch.add_object(
            properties={},
            collection="Test",
            uuid=from_object_uuid,
        )
        assert batch.num_objects() == 1
        assert batch.num_references() == 0
        batch.add_object(
            properties={},
            collection="Test",
            uuid=to_object_uuid,
        )
        assert batch.num_objects() == 2
        assert batch.num_references() == 0
        batch.add_reference(
            from_object_uuid=from_object_uuid,
            from_object_collection="Test",
            from_property_name="test",
            to_object_uuid=to_object_uuid,
            to_object_collection=to_object_collection,
        )
        assert batch.num_objects() == 2
        assert batch.num_references() == 1
    objs = client_sync_indexing.collections.get("Test").query.fetch_objects().objects
    obj = client_sync_indexing.collections.get("Test").query.fetch_object_by_id(from_object_uuid)
    assert len(objs) == 2
    print(obj.properties)
    assert isinstance(obj.properties["test"][0]["beacon"], str)


def test_add_data_object_and_get_class_shards_readiness(
    client_sync_indexing: weaviate.WeaviateClient,
):
    """Test the `add_data_object` method"""
    client_sync_indexing.batch.add_object(
        properties={},
        collection="Test",
    )
    client_sync_indexing.batch.create_objects()
    statuses = client_sync_indexing.batch._get_shards_readiness(Shard(collection="Test"))
    assert len(statuses) == 1
    assert statuses[0]


def test_add_data_object_with_tenant_and_get_class_shards_readiness(
    client_sync_indexing: weaviate.WeaviateClient,
):
    """Test the `add_data_object` method"""
    client_sync_indexing.collections.delete_all()
    test = client_sync_indexing.collections.create(
        name="Test",
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    test.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    client_sync_indexing.batch.add_object(
        properties={},
        collection="Test",
        tenant="tenant1",
    )
    client_sync_indexing.batch.create_objects()
    statuses = client_sync_indexing.batch._get_shards_readiness(
        Shard(collection="Test", tenant="tenant1")
    )
    assert len(statuses) == 1
    assert statuses[0]


def test_add_object_batch_with_tenant(client_sync_indexing: weaviate.WeaviateClient):
    # create two classes and add 5 tenants each
    collections = ["BatchTestMultiTenant1", "BatchTestMultiTenant2"]
    for name in collections:
        client_sync_indexing.collections.create(
            name=name,
            properties=[
                Property(name="tenantAsProp", data_type=DataType.TEXT),
            ],
            multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        )
        client_sync_indexing.collections.get(name).tenants.create(
            [Tenant(name="tenant" + str(i)) for i in range(5)]
        )

    nr_objects = 100
    objects = []
    with client_sync_indexing.batch as batch:
        for i in range(nr_objects):
            obj_uuid = uuid.uuid4()
            objects.append((obj_uuid, collections[i % 2], "tenant" + str(i % 5)))
            batch.add_object(
                collection=collections[i % 2],
                tenant="tenant" + str(i % 5),
                properties={"tenantAsProp": "tenant" + str(i % 5)},
                uuid=obj_uuid,
            )

    for obj in objects:
        retObj = (
            client_sync_indexing.collections.get(obj[1])
            .with_tenant(obj[2])
            .query.fetch_object_by_id(obj[0])
        )
        assert retObj.properties["tenantAsProp"] == obj[2]

    for name in collections:
        client_sync_indexing.collections.delete(name)


def test_add_ref_batch_with_tenant(client_sync_indexing: weaviate.WeaviateClient):
    client_sync_indexing.collections.delete_all()

    # create two classes and add 5 tenants each
    collections = ["BatchRefTestMultiTenant0", "BatchRefTestMultiTenant1"]
    client_sync_indexing.collections.create(
        name=collections[0],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    client_sync_indexing.collections.create(
        name=collections[1],
        properties=[
            Property(name="tenantAsProp", data_type=DataType.TEXT),
            ReferenceProperty(name="ref", target_collection=collections[0]),
        ],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    for name in collections:
        client_sync_indexing.collections.get(name).tenants.create(
            [Tenant(name="tenant" + str(i)) for i in range(5)]
        )

    nr_objects = 100
    objects_class0 = []
    objects_class1 = []
    with client_sync_indexing.batch as batch:
        for i in range(nr_objects):
            tenant = "tenant" + str(i % 5)
            obj_uuid0 = uuid.uuid4()
            objects_class0.append(obj_uuid0)
            batch.add_object(
                collection=collections[0], tenant=tenant, properties={}, uuid=obj_uuid0
            )

            obj_uuid1 = uuid.uuid4()
            objects_class1.append((obj_uuid1, "tenant" + str(i % 5)))
            batch.add_object(
                collection=collections[1],
                tenant=tenant,
                properties={"tenantAsProp": tenant},
                uuid=obj_uuid1,
            )

            # add refs between classes for all tenants
            batch.add_reference(
                from_property_name="ref",
                from_object_collection=collections[1],
                from_object_uuid=obj_uuid1,
                to_object_collection=collections[0],
                to_object_uuid=obj_uuid0,
                tenant=tenant,
            )

    for i, obj in enumerate(objects_class1):
        ret_obj = (
            client_sync_indexing.collections.get(collections[1])
            .with_tenant(obj[1])
            .query.fetch_object_by_id(obj[0])
        )
        assert ret_obj.properties["tenantAsProp"] == obj[1]
        assert (
            ret_obj.properties["ref"][0]["beacon"]
            == f"weaviate://localhost/{collections[0]}/{objects_class0[i]}"
        )

    for name in reversed(collections):
        client_sync_indexing.collections.delete(name)


def test_add_ten_thousand_data_objects(client_sync_indexing: weaviate.WeaviateClient):
    """Test adding ten thousand data objects"""
    nr_objects = 10000
    client_sync_indexing.batch.configure(num_workers=4)
    with client_sync_indexing.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection="Test",
                properties={"name": "test" + str(i)},
            )
    objs = (
        client_sync_indexing.collections.get("Test").query.fetch_objects(limit=nr_objects).objects
    )
    assert len(objs) == nr_objects
    client_sync_indexing.collections.delete("Test")


def make_refs(uuids: List[uuid.UUID]) -> List[dict]:
    refs = []
    for from_ in uuids:
        tos = uuids.copy()
        tos.remove(from_)
        for to in tos:
            refs.append(
                {
                    "from_object_uuid": from_,
                    "from_object_collection": "Test",
                    "from_property_name": "test",
                    "to_object_uuid": to,
                    "to_object_collection": "Test",
                }
            )
    return refs


def test_add_one_hundred_objects_and_references_between_all(
    client_sync_indexing: weaviate.WeaviateClient,
):
    """Test adding one hundred objects and references between all of them"""

    nr_objects = 100
    client_sync_indexing.batch.configure(num_workers=4)
    uuids: List[uuid.UUID] = []
    with client_sync_indexing.batch as batch:
        for i in range(nr_objects):
            uuid_ = batch.add_object(
                collection="Test",
                properties={"name": "test" + str(i)},
            )
            uuids.append(uuid_)
        for ref in make_refs(uuids):
            batch.add_reference(**ref)
    objs = (
        client_sync_indexing.collections.get("Test")
        .query.fetch_objects(limit=nr_objects, return_properties=FromReference(link_on="test"))
        .objects
    )
    assert len(objs) == nr_objects
    for obj in objs:
        assert len(obj.properties["test"].objects) == nr_objects - 1
    client_sync_indexing.collections.delete("Test")


def test_add_bad_prop(client_sync_indexing: weaviate.WeaviateClient):
    """Test adding a data object with a bad property"""
    with warnings.catch_warnings():
        # Tests that no warning is emitted when the batch is not configured to retry failed objects
        client_sync_indexing.batch.configure(retry_failed_objects=True)
        with client_sync_indexing.batch as batch:
            batch.add_object(
                collection="Test",
                properties={"bad": "test"},
            )
        assert len(client_sync_indexing.batch.failed_objects()) == 1

    with pytest.warns(UserWarning):
        # Tests that a warning is emitted when the batch is configured to retry failed objects
        client_sync_indexing.batch.configure(retry_failed_objects=True)
        with client_sync_indexing.batch as batch:
            batch.add_object(
                collection="Test",
                properties={"bad": "test"},
            )
        assert len(client_sync_indexing.batch.failed_objects()) == 1


def test_add_bad_ref(client_sync_indexing: weaviate.WeaviateClient):
    """Test adding a reference with a bad property name"""
    with warnings.catch_warnings():
        # Tests that no warning is emitted when the batch is not configured to retry failed references
        client_sync_indexing.batch.configure(retry_failed_references=True)
        with client_sync_indexing.batch as batch:
            batch.add_reference(
                from_object_uuid=uuid.uuid4(),
                from_object_collection="Test",
                from_property_name="bad",
                to_object_uuid=uuid.uuid4(),
                to_object_collection="Test",
            )
        assert len(client_sync_indexing.batch.failed_references()) == 1

    with pytest.warns(UserWarning):
        # Tests that a warning is emitted when the batch is configured to retry failed references
        client_sync_indexing.batch.configure(retry_failed_references=True)
        with client_sync_indexing.batch as batch:
            batch.add_reference(
                from_object_uuid=uuid.uuid4(),
                from_object_collection="Test",
                from_property_name="bad",
                to_object_uuid=uuid.uuid4(),
                to_object_collection="Test",
            )
        assert len(client_sync_indexing.batch.failed_references()) == 1


def test_manual_batching(client_sync_indexing: weaviate.WeaviateClient):
    client_sync_indexing.batch.configure(dynamic=False, batch_size=None)
    uuids: List[uuid.UUID] = []
    for _ in range(10):
        uuid_ = client_sync_indexing.batch.add_object(
            collection="Test",
            properties={"name": "test"},
        )
        uuids.append(uuid_)
        if client_sync_indexing.batch.num_objects() == 5:
            ret = client_sync_indexing.batch.create_objects()
            assert ret.has_errors is False

    for ref in make_refs(uuids):
        client_sync_indexing.batch.add_reference(**ref)
        if client_sync_indexing.batch.num_references() == 5:
            ret = client_sync_indexing.batch.create_references()
            assert ret.has_errors is False

    objs = client_sync_indexing.collections.get("Test").query.fetch_objects().objects
    assert len(objs) == 10


def test_add_1000_objects_with_async_indexing_and_wait(
    client_async_indexing: weaviate.WeaviateClient,
):
    name = "BatchTestAsyncTenants"
    client_async_indexing.collections.delete(name)
    test = client_async_indexing.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
    )
    nr_objects = 1000
    objs = [
        {
            "collection": name,
            "properties": {"text": "text" + str(i)},
            "vector": list(range(1000)),
        }
        for i in range(nr_objects)
    ]
    with client_async_indexing.batch as batch:
        for obj in objs:
            batch.add_object(**obj)
    assert len(client_async_indexing.batch.failed_objects()) == 0
    client_async_indexing.batch.wait_for_vector_indexing()
    ret = test.aggregate.over_all(total_count=True)
    assert ret.total_count == nr_objects

    old_client = weaviate.Client("http://localhost:8090")
    assert old_client.schema.get_class_shards(name)[0]["status"] == "READY"
    assert old_client.schema.get_class_shards(name)[0]["vectorQueueSize"] == 0


def test_add_10000_objects_with_async_indexing_and_dont_wait(
    client_async_indexing: weaviate.WeaviateClient,
):
    name = "BatchTestAsyncTenants"
    client_async_indexing.collections.delete(name)
    test = client_async_indexing.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
    )
    nr_objects = 10000
    objs = [
        {
            "collection": name,
            "properties": {"text": "text" + str(i)},
            "vector": list(range(1000)),
        }
        for i in range(nr_objects)
    ]
    with client_async_indexing.batch as batch:
        for obj in objs:
            batch.add_object(**obj)
    assert len(client_async_indexing.batch.failed_objects()) == 0
    ret = test.aggregate.over_all(total_count=True)
    assert ret.total_count == nr_objects

    old_client = weaviate.Client("http://localhost:8090")
    assert old_client.schema.get_class_shards(name)[0]["status"] == "INDEXING"
    assert old_client.schema.get_class_shards(name)[0]["vectorQueueSize"] > 0


def test_add_1000_tenant_objects_with_async_indexing_and_wait_for_all(
    client_async_indexing: weaviate.WeaviateClient,
):
    name = "BatchTestAsyncTenants"
    client_async_indexing.collections.delete(name)
    test = client_async_indexing.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
    )
    tenants = [Tenant(name="tenant" + str(i)) for i in range(5)]
    test.tenants.create(tenants)
    nr_objects = 1000
    objs = [
        {
            "collection": name,
            "properties": {"text": "text" + str(i)},
            "vector": list(range(1000)),
            "tenant": tenants[i % 5].name,
        }
        for i in range(nr_objects)
    ]
    with client_async_indexing.batch as batch:
        for obj in objs:
            batch.add_object(**obj)
    assert len(client_async_indexing.batch.failed_objects()) == 0
    client_async_indexing.batch.wait_for_vector_indexing()
    for tenant in tenants:
        ret = test.with_tenant(tenant.name).aggregate.over_all(total_count=True)
        assert ret.total_count == nr_objects / len(tenants)
    old_client = weaviate.Client("http://localhost:8090")
    for shard in old_client.schema.get_class_shards(name):
        assert shard["status"] == "READY"
        assert shard["vectorQueueSize"] == 0


def test_add_10000_tenant_objects_with_async_indexing_and_wait_for_only_one(
    client_async_indexing: weaviate.WeaviateClient,
):
    name = "BatchTestAsyncTenants"
    client_async_indexing.collections.delete(name)
    test = client_async_indexing.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
    )
    tenants = [Tenant(name="tenant" + str(i)) for i in range(2)]
    test.tenants.create(tenants)
    nr_objects = 10000
    objs = [
        {
            "collection": name,
            "properties": {"text": "text" + str(i)},
            "vector": list(range(1000)),
            "tenant": tenants[0].name if i < 100 else tenants[1].name,
        }
        for i in range(nr_objects)
    ]
    with client_async_indexing.batch as batch:
        for obj in objs:
            batch.add_object(**obj)
    assert len(client_async_indexing.batch.failed_objects()) == 0
    client_async_indexing.batch.wait_for_vector_indexing(
        shards=[Shard(collection=name, tenant="tenant0")]
    )
    for tenant in tenants:
        ret = test.with_tenant(tenant.name).aggregate.over_all(total_count=True)
        assert ret.total_count == 100 if tenant.name == tenants[0].name else 900
    old_client = weaviate.Client("http://localhost:8090")
    for shard in old_client.schema.get_class_shards(name):
        if shard["name"] == "tenant0":
            assert shard["status"] == "READY"
            assert shard["vectorQueueSize"] == 0
        else:
            assert shard["status"] == "INDEXING"
            assert shard["vectorQueueSize"] > 0

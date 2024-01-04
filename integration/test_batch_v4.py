import uuid
import warnings
from dataclasses import dataclass
from typing import Generator, List, Optional, Sequence, Protocol, Tuple, Callable

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from integration.conftest import _sanitize_collection_name
from weaviate.collections.classes.batch import Shard
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
)
from weaviate.collections.classes.internal import FromReference, _CrossReference
from weaviate.collections.classes.tenants import Tenant
from weaviate.types import UUID

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")
UUID2 = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
UUID3 = uuid.UUID("83d99755-9deb-4b16-8431-d1dff4ab0a75")
UUID4 = uuid.UUID("385c992b-452a-4f71-a5d9-b161f51b540d")
UUID5 = uuid.UUID("0a4d16b3-c418-40d3-a6b7-51f87c7a603b")
UUID6 = uuid.UUID("c8a201b6-fdd2-48d1-a8ee-289a540b1b4b")


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


class ClientFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self, name: str = "", ports: Tuple[int, int] = (8080, 50051), multi_tenant: bool = False
    ) -> Tuple[weaviate.WeaviateClient, str]:
        """Typing for fixture."""
        ...


@pytest.fixture
def client_factory(
    request: SubRequest,
) -> Generator[
    Callable[[str, Tuple[int, int], bool], Tuple[weaviate.WeaviateClient, str]], None, None
]:
    name_fixture: Optional[str] = None
    client_fixture: Optional[weaviate.WeaviateClient] = None

    def _factory(
        name: str = "", ports: Tuple[int, int] = (8080, 50051), multi_tenant: bool = False
    ) -> Tuple[weaviate.WeaviateClient, str]:
        nonlocal client_fixture, name_fixture
        name_fixture = _sanitize_collection_name(request.node.name) + name
        client_fixture = weaviate.connect_to_local(grpc_port=ports[1], port=ports[0])
        client_fixture.collections.delete(name_fixture)

        client_fixture.collections.create(
            name=name_fixture,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
            references=[ReferenceProperty(name="test", target_collection=name_fixture)],
            multi_tenancy_config=Configure.multi_tenancy(multi_tenant),
        )
        return client_fixture, name_fixture

    yield _factory
    if client_fixture is not None and name_fixture is not None:
        client_fixture.collections.delete(name_fixture)


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uid", [None, UUID1, str(UUID2), UUID3.hex])
def test_add_object(
    client_factory: ClientFactory,
    uid: Optional[UUID],
    vector: Optional[Sequence],
) -> None:
    client, name = client_factory()
    with client.batch as batch:
        batch.add_object(collection=name, properties={}, uuid=uid, vector=vector)
    objs = client.collections.get(name).query.fetch_objects().objects
    assert len(objs) == 1


@pytest.mark.parametrize("from_object_uuid", [UUID1, str(UUID2), UUID3.hex])
@pytest.mark.parametrize("to_object_uuid", [UUID4.hex, UUID5, str(UUID6)])
@pytest.mark.parametrize("to_object_collection", [False, True])
def test_add_reference(
    client_factory: ClientFactory,
    from_object_uuid: UUID,
    to_object_uuid: UUID,
    to_object_collection: Optional[bool],
) -> None:
    """Test the `add_reference` method"""
    client, name = client_factory()
    with client.batch as batch:
        batch.add_object(
            properties={},
            collection=name,
            uuid=from_object_uuid,
        )
        batch.add_object(
            properties={},
            collection=name,
            uuid=to_object_uuid,
        )
        batch.add_reference(
            from_object_uuid=from_object_uuid,
            from_object_collection=name,
            from_property_name="test",
            to_object_uuid=to_object_uuid,
            to_object_collection=name if to_object_collection else None,
        )
    objs = (
        client.collections.get(name)
        .query.fetch_objects(return_references=FromReference(link_on="test"))
        .objects
    )
    obj = client.collections.get(name).query.fetch_object_by_id(
        from_object_uuid, return_references=FromReference(link_on="test")
    )
    assert len(objs) == 2
    assert isinstance(obj.references["test"], _CrossReference)


def test_add_data_object_and_get_class_shards_readiness(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client, name = client_factory()

    with client.batch as batch:
        batch.add_object(properties={}, collection=request.node.name)
    statuses = client.batch._get_shards_readiness(Shard(collection=name))
    assert len(statuses) == 1
    assert statuses[0]


def test_add_data_object_with_tenant_and_get_class_shards_readiness(
    client_factory: ClientFactory,
) -> None:
    """Test the `add_data_object` method"""
    client, name = client_factory(multi_tenant=True)
    client.collections.get(name).tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    with client.batch as batch:
        batch.add_object(properties={}, collection=name, tenant="tenant1")
    statuses = client.batch._get_shards_readiness(Shard(collection=name, tenant="tenant1"))
    assert len(statuses) == 1
    assert statuses[0]


def test_add_object_batch_with_tenant(client_factory: ClientFactory, request: SubRequest) -> None:
    # create two classes and add 5 tenants each
    tenants = [Tenant(name="tenant" + str(i)) for i in range(5)]
    client, name1 = client_factory(request.node.name + "1", multi_tenant=True)
    _, name2 = client_factory(
        request.node.name + "2", multi_tenant=True
    )  # to enable automatic cleanup
    client.collections.get(name1).tenants.create(tenants)
    client.collections.get(name2).tenants.create(tenants)

    nr_objects = 100
    objects = []
    with client.batch as batch:
        for i in range(nr_objects):
            obj_uuid = uuid.uuid4()
            objects.append((obj_uuid, name1 if i % 2 else name2, "tenant" + str(i % 5)))
            batch.add_object(
                collection=name1 if i % 2 else name2,
                tenant="tenant" + str(i % 5),
                properties={"name": "tenant" + str(i % 5)},
                uuid=obj_uuid,
            )

    for obj in objects:
        retObj = client.collections.get(obj[1]).with_tenant(obj[2]).query.fetch_object_by_id(obj[0])
        assert retObj.properties["name"] == obj[2]


def test_add_ref_batch_with_tenant(client_factory: ClientFactory, request: SubRequest) -> None:
    client, name = client_factory(multi_tenant=True)
    client.collections.get(name).tenants.create([Tenant(name="tenant" + str(i)) for i in range(5)])

    nr_objects = 100
    objects_class0 = []
    with client.batch as batch:
        for i in range(nr_objects):
            tenant = "tenant" + str(i % 5)
            obj_uuid0 = uuid.uuid4()
            objects_class0.append((obj_uuid0, tenant))
            batch.add_object(
                collection=name, tenant=tenant, properties={"name": tenant}, uuid=obj_uuid0
            )

            # add refs between all tenants
            batch.add_reference(
                from_property_name="test",
                from_object_collection=name,
                from_object_uuid=obj_uuid0,
                to_object_collection=name,
                to_object_uuid=obj_uuid0,
                tenant=tenant,
            )

    for obj in objects_class0:
        ret_obj = (
            client.collections.get(name)
            .with_tenant(obj[1])
            .query.fetch_object_by_id(
                obj[0],
                return_properties="name",
                return_references=FromReference(link_on="test"),
            )
        )
        assert ret_obj is not None
        assert ret_obj.properties["name"] == obj[1]
        assert ret_obj.references["test"].objects[0].uuid == obj[0]


def test_add_ten_thousand_data_objects(client_factory: ClientFactory, request: SubRequest) -> None:
    """Test adding ten thousand data objects"""
    client, name = client_factory()

    nr_objects = 10000
    with client.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "test" + str(i)},
            )
    objs = client.collections.get(name).query.fetch_objects(limit=nr_objects).objects
    assert len(objs) == nr_objects
    client.collections.delete(name)


def make_refs(uuids: List[UUID], name: str) -> List[dict]:
    refs = []
    for from_ in uuids:
        tos = uuids.copy()
        tos.remove(from_)
        for to in tos:
            refs.append(
                {
                    "from_object_uuid": from_,
                    "from_object_collection": name,
                    "from_property_name": "test",
                    "to_object_uuid": to,
                    "to_object_collection": name,
                }
            )
    return refs


def test_add_one_hundred_objects_and_references_between_all(client_factory: ClientFactory) -> None:
    """Test adding one hundred objects and references between all of them"""
    client, name = client_factory()
    nr_objects = 100
    uuids: List[UUID] = []
    with client.batch as batch:
        for i in range(nr_objects):
            uuid_ = batch.add_object(
                collection=name,
                properties={"name": "test" + str(i)},
            )
            uuids.append(uuid_)
        for ref in make_refs(uuids, name):
            batch.add_reference(**ref)
    objs = (
        client.collections.get(name)
        .query.fetch_objects(limit=nr_objects, return_references=FromReference(link_on="test"))
        .objects
    )
    assert len(objs) == nr_objects
    for obj in objs:
        assert len(obj.references["test"].objects) == nr_objects - 1
    client.collections.delete(name)


@pytest.mark.skip("disable retrying")
def test_add_bad_prop(client_factory: ClientFactory, request: SubRequest) -> None:
    """Test adding a data object with a bad property"""
    client, name = client_factory()

    # with warnings.catch_warnings():
    #     # Tests that no warning is emitted when the batch is not configured to retry failed objects
    #     client.batch.configure(retry_failed_objects=True)
    #     with client.batch as batch:
    #         batch.add_object(collection=name, properties={"bad": "test"})
    #     assert len(client.batch.failed_objects()) == 1
    #
    # with pytest.warns(UserWarning):
    #     # Tests that a warning is emitted when the batch is configured to retry failed objects
    #     client.batch.configure(retry_failed_objects=True)
    #     with client.batch as batch:
    #         batch.add_object(collection=name, properties={"bad": "test"})
    #     assert len(client.batch.failed_objects()) == 1


@pytest.mark.skip("disable retrying")
def test_add_bad_ref(client_factory: ClientFactory) -> None:
    """Test adding a reference with a bad property name"""
    client, name = client_factory()

    with warnings.catch_warnings():
        # Tests that no warning is emitted when the batch is not configured to retry failed references
        # client.batch.configure(retry_failed_references=True)
        with client.batch as batch:
            batch.add_reference(
                from_object_uuid=uuid.uuid4(),
                from_object_collection=name,
                from_property_name="bad",
                to_object_uuid=uuid.uuid4(),
                to_object_collection=name,
            )
        assert len(client.batch.failed_references()) == 1
    #
    # with pytest.warns(UserWarning):
    #     # Tests that a warning is emitted when the batch is configured to retry failed references
    #     client.batch.configure(retry_failed_references=True)
    #     with client.batch as batch:
    #         batch.add_reference(
    #             from_object_uuid=uuid.uuid4(),
    #             from_object_collection=name,
    #             from_property_name="bad",
    #             to_object_uuid=uuid.uuid4(),
    #             to_object_collection=name,
    #         )
    #     assert len(client.batch.failed_references()) == 1


def test_add_1000_objects_with_async_indexing_and_wait(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client, name = client_factory(ports=(8090, 50060))

    nr_objects = 1000
    with client.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(nr_objects)],
            )
    assert len(client.batch.failed_objects()) == 0
    client.batch.wait_for_vector_indexing()
    ret = client.collections.get(name).aggregate.over_all(total_count=True)
    assert ret.total_count == nr_objects

    old_client = weaviate.Client("http://localhost:8090")
    assert old_client.schema.get_class_shards(name)[0]["status"] == "READY"
    assert old_client.schema.get_class_shards(name)[0]["vectorQueueSize"] == 0


@pytest.mark.skip("Difficult to find numbers that work reliable in the CI")
def test_add_10000_objects_with_async_indexing_and_dont_wait(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    old_client = weaviate.Client("http://localhost:8090")
    client, name = client_factory(ports=(8090, 50060))

    nr_objects = 10000
    vec_length = 1000
    with client.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(vec_length)],
            )
    shard_status = old_client.schema.get_class_shards(name)
    assert shard_status[0]["status"] == "INDEXING"
    assert shard_status[0]["vectorQueueSize"] > 0

    assert len(client.batch.failed_objects()) == 0

    ret = client.collections.get(name).aggregate.over_all(total_count=True)
    assert ret.total_count == nr_objects


def test_add_1000_tenant_objects_with_async_indexing_and_wait_for_all(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client, name = client_factory(ports=(8090, 50060), multi_tenant=True)
    tenants = [Tenant(name="tenant" + str(i)) for i in range(2)]
    collection = client.collections.get(name)
    collection.tenants.create(tenants)
    nr_objects = 2000

    with client.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(nr_objects)],
                tenant=tenants[i % len(tenants)].name,
            )
    assert len(client.batch.failed_objects()) == 0
    client.batch.wait_for_vector_indexing()
    for tenant in tenants:
        ret = collection.with_tenant(tenant.name).aggregate.over_all(total_count=True)
        assert ret.total_count == nr_objects / len(tenants)
    old_client = weaviate.Client("http://localhost:8090")
    for shard in old_client.schema.get_class_shards(name):
        assert shard["status"] == "READY"
        assert shard["vectorQueueSize"] == 0


def test_add_10000_tenant_objects_with_async_indexing_and_wait_for_only_one(
    client_factory: ClientFactory,
) -> None:
    client, name = client_factory(ports=(8090, 50060), multi_tenant=True)
    tenants = [Tenant(name="tenant" + str(i)) for i in range(2)]
    collection = client.collections.get(name)
    collection.tenants.create(tenants)

    nr_objects = 1001

    with client.batch as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(nr_objects)],
                tenant=tenants[0].name if i < 1000 else tenants[1].name,
            )
    assert len(client.batch.failed_objects()) == 0
    client.batch.wait_for_vector_indexing(shards=[Shard(collection=name, tenant=tenants[0].name)])
    for tenant in tenants:
        ret = collection.with_tenant(tenant.name).aggregate.over_all(total_count=True)
        assert ret.total_count == 1000 if tenant.name == tenants[0].name else 1
    old_client = weaviate.Client("http://localhost:8090")
    for shard in old_client.schema.get_class_shards(name):
        if shard["name"] == tenants[0].name:
            assert shard["status"] == "READY"
            assert shard["vectorQueueSize"] == 0
        else:
            assert shard["status"] == "INDEXING"
            assert shard["vectorQueueSize"] > 0

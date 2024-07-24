import concurrent.futures
import uuid
from dataclasses import dataclass
from typing import Generator, List, Optional, Protocol, Tuple, Callable

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from weaviate import BatchClient, ClientBatchingContextManager
import weaviate.classes as wvc
from integration.conftest import _sanitize_collection_name
from weaviate.collections.classes.batch import Shard
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
)
from weaviate.collections.classes.grpc import QueryReference
from weaviate.collections.classes.internal import (
    _CrossReference,
    ReferenceToMulti,
)
from weaviate.collections.classes.tenants import Tenant
from weaviate.types import UUID, VECTORS

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")
UUID2 = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
UUID3 = uuid.UUID("83d99755-9deb-4b16-8431-d1dff4ab0a75")
UUID4 = uuid.UUID("385c992b-452a-4f71-a5d9-b161f51b540d")
UUID5 = uuid.UUID("0a4d16b3-c418-40d3-a6b7-51f87c7a603b")
UUID6 = uuid.UUID("c8a201b6-fdd2-48d1-a8ee-289a540b1b4b")


@dataclass
class MockNumpyTorch:
    """Handles numpy and pytorch vectors."""

    array: list

    def squeeze(self) -> "MockNumpyTorch":
        return self

    def tolist(self) -> list:
        return self.array


@dataclass
class MockTensorFlow:
    """Handles tensorflow vectors."""

    array: list

    def numpy(self) -> "MockNumpyTorch":
        return MockNumpyTorch(self.array)


@dataclass
class MockDFSeries:
    """Handles pandas and polars series."""

    array: list

    def to_list(self) -> list:
        return self.array


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
    name_fixtures: List[str] = []
    client_fixture: Optional[weaviate.WeaviateClient] = None

    def _factory(
        name: str = "", ports: Tuple[int, int] = (8080, 50051), multi_tenant: bool = False
    ) -> Tuple[weaviate.WeaviateClient, str]:
        nonlocal client_fixture, name_fixtures
        name_fixture = _sanitize_collection_name(request.node.name) + name
        name_fixtures.append(name_fixture)
        if client_fixture is None:
            client_fixture = weaviate.connect_to_local(grpc_port=ports[1], port=ports[0])

        if client_fixture.collections.exists(name_fixture):
            client_fixture.collections.delete(name_fixture)

        client_fixture.collections.create(
            name=name_fixture,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
            references=[ReferenceProperty(name="test", target_collection=name_fixture)],
            multi_tenancy_config=Configure.multi_tenancy(multi_tenant),
            vectorizer_config=Configure.Vectorizer.none(),
        )
        return client_fixture, name_fixture

    try:
        yield _factory
    finally:
        if client_fixture is not None and name_fixtures is not None:
            for name_fixture in name_fixtures:
                client_fixture.collections.delete(name_fixture)
        if client_fixture is not None:
            client_fixture.close()


def test_add_objects_in_multiple_batches(client_factory: ClientFactory) -> None:
    client, name = client_factory()
    with client.batch.rate_limit(50) as batch:
        batch.add_object(collection=name, properties={})
    with client.batch.dynamic() as batch:
        batch.add_object(collection=name, properties={})
    with client.batch.dynamic() as batch:
        batch.add_object(collection=name, properties={})
    objs = client.collections.get(name).query.fetch_objects().objects
    assert len(objs) == 3


def test_flushing(client_factory: ClientFactory) -> None:
    """Test that batch is working normally after flushing."""
    client, name = client_factory()
    with client.batch.dynamic() as batch:
        batch.add_object(collection=name, properties={})
        batch.flush()
        objs = client.collections.get(name).query.fetch_objects().objects
        assert len(objs) == 1
        batch.add_object(collection=name, properties={})
        batch.add_object(collection=name, properties={})
    objs = client.collections.get(name).query.fetch_objects().objects
    assert len(objs) == 3


@pytest.mark.parametrize(
    "vector",
    [
        None,
        [1, 2, 3],
        MockNumpyTorch([1, 2, 3]),
        MockTensorFlow([1, 2, 3]),
        MockDFSeries([1, 2, 3]),
    ],
)
@pytest.mark.parametrize("uid", [None, UUID1, str(UUID2), UUID3.hex])
def test_add_object(
    client_factory: ClientFactory,
    uid: Optional[UUID],
    vector: Optional[VECTORS],
) -> None:
    client, name = client_factory()
    with client.batch.fixed_size() as batch:
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
    with client.batch.fixed_size() as batch:
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
            from_uuid=from_object_uuid,
            from_collection=name,
            from_property="test",
            to=to_object_uuid,
        )
    objs = (
        client.collections.get(name)
        .query.fetch_objects(return_references=QueryReference(link_on="test"))
        .objects
    )
    obj = client.collections.get(name).query.fetch_object_by_id(
        from_object_uuid, return_references=QueryReference(link_on="test")
    )
    assert len(objs) == 2
    assert isinstance(obj.references["test"], _CrossReference)


def test_add_data_object_and_get_class_shards_readiness(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client, name = client_factory()

    with client.batch.fixed_size() as batch:
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
    with client.batch.fixed_size() as batch:
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
    with client.batch.dynamic() as batch:
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


def _from_uuid_to_uuid(uuid: uuid.UUID) -> uuid.UUID:
    return uuid


def _from_uuid_to_str(uuid: uuid.UUID) -> str:
    return str(uuid)


def _from_uuid_to_uuid_list(uuid: uuid.UUID) -> List[uuid.UUID]:
    return [uuid]


def _from_uuid_to_str_list(uuid: uuid.UUID) -> List[str]:
    return [str(uuid)]


@pytest.mark.parametrize(
    "to_ref",
    [
        _from_uuid_to_uuid,
        _from_uuid_to_str,
        _from_uuid_to_uuid_list,
        _from_uuid_to_str_list,
    ],
)
def test_add_ref_batch(client_factory: ClientFactory, to_ref: Callable) -> None:
    client, name = client_factory()

    nr_objects = 100
    objects_class0 = []
    with client.batch.dynamic() as batch:
        for _ in range(nr_objects):
            obj_uuid0 = uuid.uuid4()
            objects_class0.append(obj_uuid0)
            batch.add_object(collection=name, uuid=obj_uuid0)
            batch.add_reference(
                from_property="test",
                from_collection=name,
                from_uuid=obj_uuid0,
                to=to_ref(obj_uuid0),
            )

    collection = client.collections.get(name)
    for obj in objects_class0:
        ret_obj = collection.query.fetch_object_by_id(
            obj,
            return_references=QueryReference(link_on="test"),
        )
        assert ret_obj is not None
        assert ret_obj.references["test"].objects[0].uuid == obj


def test_add_ref_batch_with_tenant(client_factory: ClientFactory) -> None:
    client, name = client_factory(multi_tenant=True)
    client.collections.get(name).tenants.create([Tenant(name="tenant" + str(i)) for i in range(5)])

    nr_objects = 100
    objects_class0 = []
    with client.batch.dynamic() as batch:
        for i in range(nr_objects):
            tenant = "tenant" + str(i % 5)
            obj_uuid0 = uuid.uuid4()
            objects_class0.append((obj_uuid0, tenant))
            batch.add_object(
                collection=name, tenant=tenant, properties={"name": tenant}, uuid=obj_uuid0
            )

            # add refs between all tenants
            batch.add_reference(
                from_property="test",
                from_collection=name,
                from_uuid=obj_uuid0,
                to=ReferenceToMulti(
                    uuids=obj_uuid0, target_collection=name
                ),  # workaround for autodetection with tenant
                tenant=tenant,
            )

    for obj in objects_class0:
        ret_obj = (
            client.collections.get(name)
            .with_tenant(obj[1])
            .query.fetch_object_by_id(
                obj[0],
                return_properties="name",
                return_references=QueryReference(link_on="test"),
            )
        )
        assert ret_obj is not None
        assert ret_obj.properties["name"] == obj[1]
        assert ret_obj.references["test"].objects[0].uuid == obj[0]


@pytest.mark.parametrize(
    "batching_method",
    [
        lambda client: client.batch.dynamic(),
        lambda client: client.batch.fixed_size(),
        lambda client: client.batch.rate_limit(9999),
    ],
    ids=[
        "test_add_ten_thousand_data_objects_dynamic",
        "test_add_ten_thousand_data_objects_fixed_size",
        "test_add_ten_thousand_data_objects_rate_limit",
    ],
)
def test_add_ten_thousand_data_objects(
    client_factory: ClientFactory,
    batching_method: Callable[[weaviate.WeaviateClient], ClientBatchingContextManager],
    request: SubRequest,
) -> None:
    """Test adding ten thousand data objects"""
    client, name = client_factory()

    nr_objects = 10000
    with batching_method(client) as batch:
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
                    "from_uuid": from_,
                    "from_collection": name,
                    "from_property": "test",
                    "to": to,
                }
            )
    return refs


def test_add_one_hundred_objects_and_references_between_all(
    client_factory: ClientFactory,
) -> None:
    """Test adding one hundred objects and references between all of them"""
    client, name = client_factory()
    nr_objects = 100
    uuids: List[UUID] = []
    with client.batch.dynamic() as batch:
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
        .query.fetch_objects(limit=nr_objects, return_references=QueryReference(link_on="test"))
        .objects
    )
    assert len(objs) == nr_objects
    for obj in objs:
        assert len(obj.references["test"].objects) == nr_objects - 1
    client.collections.delete(name)


def test_add_1000_objects_with_async_indexing_and_wait(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client, name = client_factory(ports=(8090, 50061))

    nr_objects = 1000
    with client.batch.dynamic() as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(nr_objects)],
            )
    assert len(client.batch.failed_objects) == 0
    client.batch.wait_for_vector_indexing()
    ret = client.collections.get(name).aggregate.over_all(total_count=True)
    assert ret.total_count == nr_objects

    shards = client.collections.get(name).config.get_shards()
    assert shards[0].status == "READY"
    assert shards[0].vector_queue_size == 0


@pytest.mark.skip("Difficult to find numbers that work reliably in the CI")
def test_add_10000_objects_with_async_indexing_and_dont_wait(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    old_client = weaviate.Client("http://localhost:8090")
    client, name = client_factory(ports=(8090, 50061))

    nr_objects = 10000
    vec_length = 1000
    with client.batch.fixed_size(batch_size=1000, concurrent_requests=1) as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(vec_length)],
            )
    shard_status = old_client.schema.get_class_shards(name)
    assert shard_status[0]["status"] == "INDEXING"
    assert shard_status[0]["vectorQueueSize"] > 0

    assert len(client.batch.failed_objects) == 0

    ret = client.collections.get(name).aggregate.over_all(total_count=True)
    assert ret.total_count == nr_objects


def test_add_1000_tenant_objects_with_async_indexing_and_wait_for_all(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client, name = client_factory(ports=(8090, 50061), multi_tenant=True)
    tenants = [Tenant(name="tenant" + str(i)) for i in range(2)]
    collection = client.collections.get(name)
    collection.tenants.create(tenants)
    nr_objects = 2000

    with client.batch.dynamic() as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(nr_objects)],
                tenant=tenants[i % len(tenants)].name,
            )
    assert len(client.batch.failed_objects) == 0
    client.batch.wait_for_vector_indexing()
    for tenant in tenants:
        ret = collection.with_tenant(tenant.name).aggregate.over_all(total_count=True)
        assert ret.total_count == nr_objects / len(tenants)

    shards = client.collections.get(name).config.get_shards()
    for shard in shards:
        assert shard.status == "READY"
        assert shard.vector_queue_size == 0


@pytest.mark.skip("Difficult to find numbers that work reliably in the CI")
def test_add_1000_tenant_objects_with_async_indexing_and_wait_for_only_one(
    client_factory: ClientFactory,
) -> None:
    client, name = client_factory(ports=(8090, 50061), multi_tenant=True)
    tenants = [Tenant(name="tenant" + str(i)) for i in range(2)]
    collection = client.collections.get(name)
    collection.tenants.create(tenants)

    nr_objects = 1001

    with client.batch.dynamic() as batch:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "text" + str(i)},
                vector=[float((j + i) % nr_objects) / nr_objects for j in range(nr_objects)],
                tenant=tenants[0].name if i < 1000 else tenants[1].name,
            )
    assert len(client.batch.failed_objects) == 0
    assert len(client.batch.results.objs.all_responses) == 1001
    client.batch.wait_for_vector_indexing(shards=[Shard(collection=name, tenant=tenants[0].name)])
    for tenant in tenants:
        ret = collection.with_tenant(tenant.name).aggregate.over_all(total_count=True)
        assert ret.total_count == 1000 if tenant.name == tenants[0].name else 1

    shards = client.collections.get(name).config.get_shards()
    for shard in shards:
        if shard.name == tenants[0].name:
            assert shard.status == "READY"
            assert shard.vector_queue_size == 0
        else:
            assert shard.status == "INDEXING"
            assert shard.vector_queue_size > 0


@pytest.mark.parametrize(
    "batching_method",
    [
        lambda client: client.batch.dynamic(),
        lambda client: client.batch.fixed_size(),
        lambda client: client.batch.rate_limit(1000),
    ],
    ids=[
        "test_add_one_hundred_objects_and_references_between_all_dynamic",
        "test_add_one_hundred_objects_and_references_between_all_fixed_size",
        "test_add_one_hundred_objects_and_references_between_all_rate_limit",
    ],
)
def test_add_one_object_and_a_self_reference(
    client_factory: ClientFactory,
    batching_method: Callable[[weaviate.WeaviateClient], ClientBatchingContextManager],
) -> None:
    """Test adding one object and a self reference"""
    client, name = client_factory()
    with batching_method(client) as batch:
        uuid = batch.add_object(collection=name, properties={})
        batch.add_reference(
            from_uuid=uuid,
            from_collection=name,
            from_property="test",
            to=uuid,
        )
    obj = client.collections.get(name).query.fetch_object_by_id(
        uuid, return_references=QueryReference(link_on="test")
    )
    assert obj is not None
    assert obj.references["test"].objects[0].uuid == uuid


def test_multi_threaded_batching(
    client_factory: ClientFactory,
) -> None:
    client, name = client_factory()
    nr_objects = 1000
    nr_threads = 10

    def batch_insert(batch: BatchClient) -> None:
        for i in range(nr_objects):
            batch.add_object(
                collection=name,
                properties={"name": "test" + str(i)},
            )

    with concurrent.futures.ThreadPoolExecutor() as executor:
        with client.batch.dynamic() as batch:
            futures = [executor.submit(batch_insert, batch) for _ in range(nr_threads)]
    for future in concurrent.futures.as_completed(futures):
        future.result()
    objs = client.collections.get(name).query.fetch_objects(limit=nr_objects * nr_threads).objects
    assert len(objs) == nr_objects * nr_threads


def test_error_reset(client_factory: ClientFactory) -> None:
    client, name = client_factory()
    with client.batch.dynamic() as batch:
        batch.add_object(properties={"name": 1}, collection=name)
        batch.add_object(properties={"name": "correct"}, collection=name)

    errs = client.batch.failed_objects

    assert len(errs) == 1
    assert errs[0].object_.properties is not None
    assert errs[0].object_.properties["name"] == 1

    with client.batch.dynamic() as batch:
        batch.add_object(properties={"name": 2}, collection=name)
        batch.add_object(properties={"name": "correct"}, collection=name)

    errs2 = client.batch.failed_objects
    assert len(errs2) == 1
    assert errs2[0].object_.properties is not None
    assert errs2[0].object_.properties["name"] == 2

    # err still contains original errors
    assert len(errs) == 1
    assert errs[0].object_.properties is not None
    assert errs[0].object_.properties["name"] == 1


def test_non_existant_collection(client_factory: ClientFactory) -> None:
    client, _ = client_factory()
    with client.batch.dynamic() as batch:
        batch.add_object(properties={"name": 2}, collection="DoesNotExist")

    # above should not throw - depending on the autoschema config this might create an error or
    # not, so we do not check for errors here


def test_number_of_stored_results_in_batch(client_factory: ClientFactory) -> None:
    client, name = client_factory()
    with client.batch.dynamic() as batch:
        for i in range(99999):
            batch.add_object(properties={"name": str(i)}, collection=name)

    assert len(client.batch.results.objs.all_responses) == 99999
    assert len(client.batch.results.objs.errors) == 0
    assert len(client.batch.results.objs.uuids) == 99999
    assert sorted(client.batch.results.objs.uuids.keys()) == list(range(99999))

    with client.batch.dynamic() as batch:
        for i in range(100001):
            batch.add_object(properties={"name": str(i)}, collection=name)

    assert len(client.batch.results.objs.all_responses) == 100000
    assert len(client.batch.results.objs.errors) == 0
    assert len(client.batch.results.objs.uuids) == 100000
    assert sorted(client.batch.results.objs.uuids.keys()) == list(range(1, 100001))

    # depending on timings in the event loop, some batches may end before others
    # as such the keys of the uuids dict may not be in order but they are still unique
    # and correspond to the original indices within the batch


def test_uuids_keys_and_original_index(client_factory: ClientFactory) -> None:
    client, name = client_factory()
    objs = [(uuid.uuid4(), {"name": str(i)}) for i in range(100)]
    with client.batch.dynamic() as batch:
        for obj in objs:
            batch.add_object(uuid=obj[0], properties=obj[1], collection=name)

    assert len(client.batch.results.objs.all_responses) == 100
    assert len(client.batch.results.objs.errors) == 0
    assert len(client.batch.results.objs.uuids) == 100

    assert [objs[k][0] for k in client.batch.results.objs.uuids.keys()] == list(
        client.batch.results.objs.uuids.values()
    )


def test_batching_error_logs(
    client_factory: ClientFactory, caplog: pytest.LogCaptureFixture
) -> None:
    client, name = client_factory()
    with client.batch.fixed_size() as batch:
        for obj in [{"name": i} for i in range(100)]:
            batch.add_object(properties=obj, collection=name)
    assert (
        "Failed to send 100 objects in a batch of 100. Please inspect client.batch.failed_objects or collection.batch.failed_objects for the failed objects."
        in caplog.text
    )


def test_references_with_to_uuids(client_factory: ClientFactory) -> None:
    """Test that batch waits until the to object is created."""
    client, _ = client_factory()

    client.collections.delete(["target", "source"])
    target = client.collections.create(
        "target", multi_tenancy_config=wvc.config.Configure.multi_tenancy(enabled=True)
    )
    source = client.collections.create(
        "source",
        references=[wvc.config.ReferenceProperty(name="to", target_collection="target")],
        multi_tenancy_config=wvc.config.Configure.multi_tenancy(enabled=True),
    )

    target.tenants.create("tenant-1")
    source.tenants.create("tenant-1")
    from_uuid = source.with_tenant("tenant-1").data.insert(properties={})
    objs = 20

    with client.batch.fixed_size(batch_size=10, concurrent_requests=1) as batch:
        for _ in range(objs):
            to = batch.add_object(collection="target", properties={}, tenant="tenant-1")
            batch.add_reference(
                from_uuid=from_uuid,
                from_property="to",
                to=to,
                from_collection="source",
                tenant="tenant-1",
            )

    assert len(client.batch.failed_references) == 0, client.batch.failed_references
    client.collections.delete(["target", "source"])

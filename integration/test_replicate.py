import time
from typing import Any, Iterator

import pytest

import weaviate
from integration.conftest import ClientFactory, CollectionFactory
from weaviate.cluster.replicate.executor import _SCALE_PLAN_MIN_VERSIONS
from weaviate.collections import Collection
from weaviate.outputs.replication import ReplicateOperationState
from weaviate.util import _ServerVersion

PORTS = (8087, 50058)

pytestmark = pytest.mark.xdist_group(name="replicate")


def replicate_collection(collection_factory: CollectionFactory):
    dummy = collection_factory("dummy", ports=PORTS)
    if dummy._connection._weaviate_version.is_lower_than(1, 32, 0):
        pytest.skip("Replication operations require Weaviate 1.32.0 or higher")

    collection = collection_factory(
        properties=[
            weaviate.classes.config.Property(
                name="name", data_type=weaviate.classes.config.DataType.TEXT
            )
        ],
        ports=PORTS,
        replication_config=weaviate.classes.config.Configure.replication(factor=1),
    )
    time.sleep(1)  # wait of eventual consistency of collection creation
    collection.data.insert_many(
        [
            {"name": name}
            for name in [
                "Alice",
                "Bob",
                "Charlie",
                "David",
                "Eve",
                "Frank",
                "Grace",
                "Heidi",
                "Ivan",
                "Judy",
                "Karl",
                "Leo",
                "Mallory",
                "Nina",
                "Oscar",
                "Peggy",
                "Quentin",
                "Rupert",
                "Sybil",
                "Trent",
                "Uma",
                "Victor",
                "Walter",
                "Xena",
                "Yara",
                "Zane",
            ]
        ]
    )
    return collection


@pytest.fixture
def replicate_client(client_factory: ClientFactory):
    return client_factory(
        ports=PORTS,
    )


def cleanup_ops(replicate_client: weaviate.WeaviateClient):
    """Cleanup any existing replication operations before running tests."""
    replicate_client.cluster.replications.delete_all()
    while len(replicate_client.cluster.replications.list_all()) > 0:
        time.sleep(0.1)


@pytest.fixture
def scale_collection(
    collection_factory: CollectionFactory, replicate_client: weaviate.WeaviateClient
) -> Iterator[Collection[Any, Any]]:
    """Yield a one-shard collection at factor 1.

    Teardown removes its replication operations before collection_factory deletes it.
    """
    server_version = _ServerVersion.from_string(replicate_client.get_meta()["version"])
    if not server_version.is_at_least_any(*_SCALE_PLAN_MIN_VERSIONS):
        pytest.skip(
            f"Replication scale plans are unavailable on this server version. Min. required versions: {_SCALE_PLAN_MIN_VERSIONS}"
        )

    collection = collection_factory(
        properties=[
            weaviate.classes.config.Property(
                name="name", data_type=weaviate.classes.config.DataType.TEXT
            )
        ],
        ports=PORTS,
        sharding_config=weaviate.classes.config.Configure.sharding(desired_count=1),
        replication_config=weaviate.classes.config.Configure.replication(factor=1),
    )
    try:
        yield collection
    finally:
        for operation in replicate_client.cluster.replications.query(collection=collection.name):
            replicate_client.cluster.replications.delete(uuid=operation.uuid)


def test_generate_and_apply_scale_plan(
    replicate_client: weaviate.WeaviateClient, scale_collection: Collection[Any, Any]
) -> None:
    desired_replicas = 3
    object_id = scale_collection.data.insert({"name": "Alice"})

    plan = replicate_client.cluster.replications.generate_scale_plan(
        collection=scale_collection.name, replication_factor=desired_replicas
    )
    result = replicate_client.cluster.replications.apply_scale_plan(plan=plan)
    assert len(result.operation_ids) == desired_replicas - 1

    deadline = time.monotonic() + 60
    pending = set(result.operation_ids)
    while pending and time.monotonic() < deadline:
        for operation_id in list(pending):
            operation = replicate_client.cluster.replications.get(uuid=operation_id)
            if operation is None:
                continue
            assert operation.status.errors == [], operation
            assert operation.status.state != ReplicateOperationState.CANCELLED
            if operation.status.state == ReplicateOperationState.READY:
                pending.discard(operation_id)
        time.sleep(0.1)
    if pending:
        pytest.fail(f"Scale operations did not reach READY within 60s: {pending!r}")

    # READY follows the Raft placement update; this read goes to the leader.
    state = replicate_client.cluster.query_sharding_state(collection=scale_collection.name)
    assert state is not None
    assert len(state.shards) == 1
    assert len(state.shards[0].replicas) == desired_replicas

    obj = scale_collection.query.fetch_object_by_id(object_id)
    assert obj is not None
    assert obj.uuid == object_id
    assert obj.properties == {"name": "Alice"}


def test_replicate_and_get(
    replicate_client: weaviate.WeaviateClient, collection_factory: CollectionFactory
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    src_node = nodes[0].name
    tgt_node = nodes[1].name
    shard = nodes[0].shards[0].name

    cleanup_ops(replicate_client)
    op_id = replicate_client.cluster.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    op1 = replicate_client.cluster.replications.get(uuid=op_id)

    assert op1 is not None
    assert op1.collection == collection.name
    assert op1.shard == shard
    assert op1.source_node == src_node
    assert op1.target_node == tgt_node
    assert op1.transfer_type == weaviate.classes.replication.ReplicationType.COPY
    assert op1.status is not None
    assert op1.status_history is None

    op2 = replicate_client.cluster.replications.get(uuid=op_id, include_history=True)

    assert op2 is not None
    assert op2.collection == collection.name
    assert op2.shard == shard
    assert op2.source_node == src_node
    assert op2.target_node == tgt_node
    assert op2.transfer_type == weaviate.classes.replication.ReplicationType.COPY
    assert op2.status is not None
    assert op2.status_history is not None


def test_replicate_and_cancel(
    replicate_client: weaviate.WeaviateClient, collection_factory: CollectionFactory
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    src_node = nodes[0].name
    tgt_node = nodes[1].name
    shard = nodes[0].shards[0].name

    cleanup_ops(replicate_client)
    op_id = replicate_client.cluster.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    replicate_client.cluster.replications.cancel(uuid=op_id)

    start = time.time()
    while (
        not replicate_client.cluster.replications.get(uuid=op_id).status.state  # type: ignore
        == ReplicateOperationState.CANCELLED
    ):
        time.sleep(0.1)
        if time.time() - start > 10:
            raise TimeoutError("Timed out waiting for replication operation to be cancelled")


def test_replicate_and_delete(
    replicate_client: weaviate.WeaviateClient, collection_factory: CollectionFactory
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    src_node = nodes[0].name
    tgt_node = nodes[1].name
    shard = nodes[0].shards[0].name

    cleanup_ops(replicate_client)
    op_id = replicate_client.cluster.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    replicate_client.cluster.replications.delete(uuid=op_id)

    start = time.time()
    while replicate_client.cluster.replications.get(uuid=op_id) is not None:
        time.sleep(0.1)
        if time.time() - start > 10:
            raise TimeoutError("Timed out waiting for replication operation to be deleted")


def test_replicate_and_query(
    replicate_client: weaviate.WeaviateClient, collection_factory: CollectionFactory
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    src_node = nodes[0].name
    tgt_node = nodes[1].name
    shard = nodes[0].shards[0].name

    cleanup_ops(replicate_client)
    replicate_client.cluster.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    ops = replicate_client.cluster.replications.query(
        collection=collection.name,
        shard=shard,
        target_node=tgt_node,
    )
    assert len(ops) == 1

    ops = replicate_client.cluster.replications.query(
        collection=collection.name,
        shard=shard,
        target_node=src_node,
    )
    assert len(ops) == 1

    ops = replicate_client.cluster.replications.list_all()
    assert len(ops) == 1


def test_query_sharding_state(
    replicate_client: weaviate.WeaviateClient,
    collection_factory: CollectionFactory,
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    shard = nodes[0].shards[0].name

    sharding_state = replicate_client.cluster.query_sharding_state(collection=collection.name)
    assert sharding_state is not None
    assert shard in [s.name for s in sharding_state.shards]

    sharding_state = replicate_client.cluster.query_sharding_state(
        collection=collection.name, shard=shard
    )
    assert sharding_state is not None
    assert shard in [s.name for s in sharding_state.shards]

    assert (
        replicate_client.cluster.query_sharding_state(collection="non_existent_collection") is None
    )
    assert (
        replicate_client.cluster.query_sharding_state(
            collection=collection.name, shard="non_existent_shard"
        )
        is None
    )

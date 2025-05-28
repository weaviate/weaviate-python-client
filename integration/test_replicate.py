import time
import pytest
from integration.conftest import ClientFactory, CollectionFactory

import weaviate

PORTS = (8087, 50058)


def replicate_collection(collection_factory: CollectionFactory):
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


def test_replicate_and_get(
    replicate_client: weaviate.WeaviateClient, collection_factory: CollectionFactory
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    src_node = nodes[0].name
    tgt_node = nodes[1].name
    shard = nodes[0].shards[0].name

    op_id = replicate_client.replication.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    op1 = replicate_client.replication.operations.get(uuid=op_id)

    assert op1 is not None
    assert op1.collection == collection.name
    assert op1.shard == shard
    assert op1.source_node == src_node
    assert op1.target_node == tgt_node
    assert op1.transfer_type == weaviate.classes.replication.TransferType.COPY
    assert op1.status is not None
    assert op1.status_history is None

    op2 = replicate_client.replication.operations.get(uuid=op_id, include_history=True)

    assert op2 is not None
    assert op2.collection == collection.name
    assert op2.shard == shard
    assert op2.source_node == src_node
    assert op2.target_node == tgt_node
    assert op2.transfer_type == weaviate.classes.replication.TransferType.COPY
    assert op2.status is not None
    assert op2.status_history is not None

    ops = replicate_client.replication.operations.list_all()
    assert len(ops) == 1


def test_replicate_and_cancel(
    replicate_client: weaviate.WeaviateClient, collection_factory: CollectionFactory
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    src_node = nodes[0].name
    tgt_node = nodes[1].name
    shard = nodes[0].shards[0].name

    op_id = replicate_client.replication.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    replicate_client.replication.operations.cancel(uuid=op_id)

    start = time.time()
    while (
        not replicate_client.replication.operations.get(uuid=op_id).status.state  # type: ignore
        == weaviate.outputs.replication.ReplicateOperationState.CANCELLED
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

    op_id = replicate_client.replication.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    replicate_client.replication.operations.delete(uuid=op_id)

    start = time.time()
    while replicate_client.replication.operations.get(uuid=op_id) is not None:
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

    replicate_client.replication.replicate(
        collection=collection.name,
        shard=shard,
        source_node=src_node,
        target_node=tgt_node,
    )

    ops = replicate_client.replication.operations.query(
        collection=collection.name,
        shard=shard,
        target_node=tgt_node,
    )
    assert len(ops) == 1

    ops = replicate_client.replication.operations.query(
        collection=collection.name,
        shard=shard,
        target_node=src_node,
    )
    assert len(ops) == 1


def test_query_sharding_state(
    replicate_client: weaviate.WeaviateClient,
    collection_factory: CollectionFactory,
):
    collection = replicate_collection(collection_factory)

    nodes = replicate_client.cluster.nodes(collection=collection.name, output="verbose")
    shard = nodes[0].shards[0].name

    sharding_state = replicate_client.replication.query_sharding_state(collection=collection.name)
    assert sharding_state is not None
    assert shard in [s.name for s in sharding_state.shards]

    sharding_state = replicate_client.replication.query_sharding_state(
        collection=collection.name, shard=shard
    )
    assert sharding_state is not None
    assert shard in [s.name for s in sharding_state.shards]

    assert (
        replicate_client.replication.query_sharding_state(collection="non_existent_collection")
        is None
    )
    assert (
        replicate_client.replication.query_sharding_state(
            collection=collection.name, shard="non_existent_shard"
        )
        is None
    )

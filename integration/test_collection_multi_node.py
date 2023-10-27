import pytest

import weaviate
from weaviate.collections.classes.config import (
    Configure,
    Property,
    ConsistencyLevel,
    DataType,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.grpc import MetadataQuery


@pytest.fixture(scope="module")
def client():
    client = weaviate.connect_to_local(port=8087, grpc_port=50058)
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


@pytest.mark.parametrize(
    "level", [ConsistencyLevel.ONE, ConsistencyLevel.ALL, ConsistencyLevel.QUORUM]
)
def test_consistency_on_multinode(client: weaviate.WeaviateClient, level: ConsistencyLevel):
    name = "TestConsistency"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        replication_config=Configure.replication(factor=2),
    ).with_consistency_level(level)

    collection.data.insert({"name": "first"})
    ret = collection.data.insert_many(
        [DataObject(properties={"name": "second"}), DataObject(properties={"name": "third"})]
    )
    assert not ret.has_errors

    objects = collection.query.fetch_objects(
        return_metadata=MetadataQuery(is_consistent=True)
    ).objects
    for obj in objects:
        assert obj.metadata.is_consistent

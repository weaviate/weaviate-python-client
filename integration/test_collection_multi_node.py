import pytest

import weaviate
from weaviate.collection.classes.config import (
    ConfigFactory,
    Property,
    ConsistencyLevel,
    DataType,
)
from weaviate.collection.classes.data import DataObject
from weaviate.collection.classes.grpc import MetadataQuery


@pytest.fixture(scope="module")
def client():
    connection_params = weaviate.ConnectionParams(
        scheme="http", host="localhost", port=8087, grpc_port=50058
    )
    client = weaviate.Client(connection_params)
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize(
    "level", [ConsistencyLevel.ONE, ConsistencyLevel.ALL, ConsistencyLevel.QUORUM]
)
def test_consistency_on_multinode(client: weaviate.Client, level: ConsistencyLevel):
    name = "TestConsistency"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        vectorizer_config=ConfigFactory.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        replication_config=ConfigFactory.replication(factor=2),
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

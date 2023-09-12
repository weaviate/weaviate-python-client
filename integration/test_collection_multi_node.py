import pytest

import weaviate
from weaviate import Config
from weaviate.collection.classes.config import (
    ConfigFactory,
    VectorizerFactory,
    Property,
    ConsistencyLevel,
    DataType,
)
from weaviate.collection.classes.data import DataObject
from weaviate.collection.classes.grpc import MetadataQuery


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client(
        "http://localhost:8087", additional_config=Config(grpc_port_experimental=50058)
    )
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
        vectorizer_config=VectorizerFactory.none(),
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

    objects = collection.query.get(return_metadata=MetadataQuery(is_consistent=True))
    for obj in objects:
        assert obj.metadata.is_consistent

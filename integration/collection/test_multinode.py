import pytest

from weaviate.collection import Collection
from weaviate.collection.classes.config import (
    ConfigFactory,
    VectorizerFactory,
    Property,
    ConsistencyLevel,
    DataType,
)
from weaviate.collection.classes.data import DataObject
from weaviate.collection.classes.grpc import MetadataQuery


@pytest.mark.parametrize(
    "level", [ConsistencyLevel.ONE, ConsistencyLevel.ALL, ConsistencyLevel.QUORUM]
)
def test_consistency_on_multinode(collection_multinode: Collection, level: ConsistencyLevel):
    name = "TestConsistency"
    collection_multinode.delete(name)
    collection = collection_multinode.create(
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

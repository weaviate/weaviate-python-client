import pytest

from weaviate.collection.classes.config import (
    ConfigFactory,
    VectorizerFactory,
    Property,
    ConsistencyLevel,
    DataType,
)
from weaviate.collection.classes.data import DataObject
from weaviate.collection.classes.grpc import MetadataQuery

from .conftest import CollectionObjectFactory


@pytest.mark.parametrize(
    "level", [ConsistencyLevel.ONE, ConsistencyLevel.ALL, ConsistencyLevel.QUORUM], ids=[0, 1, 2]
)
def test_consistency_on_multinode(
    collection_object_factory: CollectionObjectFactory, level: ConsistencyLevel, request_id: str
):
    collection = collection_object_factory(
        rest_port=8087,
        grpc_port=50058,
        name=f"TestConsistency{request_id}",
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

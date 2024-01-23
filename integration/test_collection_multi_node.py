import pytest

from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    Property,
    ConsistencyLevel,
    DataType,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.grpc import MetadataQuery


@pytest.mark.parametrize(
    "level", [ConsistencyLevel.ONE, ConsistencyLevel.ALL, ConsistencyLevel.QUORUM]
)
def test_consistency_on_multinode(
    collection_factory: CollectionFactory, level: ConsistencyLevel
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        replication_config=Configure.replication(factor=2),
        ports=(8087, 50058),
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

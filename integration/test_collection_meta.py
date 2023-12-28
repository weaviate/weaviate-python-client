from .conftest import CollectionFactory


def test_collection_get_shards(collection_factory: CollectionFactory) -> None:
    collection = collection_factory()
    status = collection.meta.get_shards()

    assert len(status) == 1
    assert status[0].collection == collection.name
    assert status[0].name is not None
    assert status[0].object_count == 0

from integration.conftest import ClientFactory, CollectionFactory

from weaviate.classes.config import DataType, Property
from weaviate.classes.debug import DebugRESTObject


def test_get_object_single_node(
    client_factory: ClientFactory, collection_factory: CollectionFactory
) -> None:
    client = client_factory()
    collection = collection_factory(properties=[Property(name="name", data_type=DataType.TEXT)])

    uuid = collection.data.insert({"name": "John Doe"})

    debug_obj = client.debug.get_object_over_rest(collection.name, uuid)
    assert debug_obj is not None
    assert isinstance(debug_obj, DebugRESTObject)
    assert str(debug_obj.uuid) == str(uuid)

    non_existant_uuid = "00000000-0000-0000-0000-000000000000"
    debug_obj = client.debug.get_object_over_rest(collection.name, non_existant_uuid)
    assert debug_obj is None


def test_get_object_multi_node(
    client_factory: ClientFactory, collection_factory: CollectionFactory
) -> None:
    client = client_factory(ports=(8087, 50058))
    collection = collection_factory(
        ports=(8087, 50058), properties=[Property(name="name", data_type=DataType.TEXT)]
    )

    uuid = collection.data.insert({"name": "John Doe"})

    for node_name in ["node1", "node2", "node3"]:
        debug_obj = client.debug.get_object_over_rest(collection.name, uuid, node_name=node_name)
        assert debug_obj is not None
        assert str(debug_obj.uuid) == str(uuid)

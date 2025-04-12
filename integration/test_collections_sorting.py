import pytest
from integration.conftest import ClientFactory


@pytest.fixture(scope="module")
def client(client_factory: ClientFactory):
    client = client_factory()
    client.collections.delete_all()
    yield client
    client.collections.delete_all()
    client.close()


def test_collections_list_all_sorting(client):
    """Test that collections.list_all() returns collections sorted alphabetically by key."""
    # Create collections with names in non-alphabetical order
    client.collections.create(name="TestCollectionC")
    client.collections.create(name="TestCollectionA")
    client.collections.create(name="TestCollectionB")

    # Get all collections
    collections = client.collections.list_all()
    
    # Get the keys and filter only our test collections
    collection_keys = list(collections.keys())
    test_collections = [k for k in collection_keys if k.startswith("TestCollection")]
    
    # Verify they are in alphabetical order
    assert test_collections == sorted(test_collections)
    
    # Test with simple=False as well
    collections = client.collections.list_all(simple=False)
    collection_keys = list(collections.keys())
    test_collections = [k for k in collection_keys if k.startswith("TestCollection")]
    assert test_collections == sorted(test_collections)
    
    # Clean up
    client.collections.delete(["TestCollectionA", "TestCollectionB", "TestCollectionC"])

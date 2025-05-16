import pytest

from integration.conftest import ClientFactory


@pytest.fixture
def sorting_test_client(client_factory: ClientFactory):
    client = client_factory()
    try:
        yield client
    finally:
        client.close()


def test_collections_list_all_sorting(sorting_test_client):
    """Test that collections.list_all() returns collections sorted alphabetically by key."""
    client = sorting_test_client

    try:
        # Create collections with names in non-alphabetical order
        client.collections.create(name="SortingTestCollectionC")
        client.collections.create(name="SortingTestCollectionA")
        client.collections.create(name="SortingTestCollectionB")

        # Get all collections
        collections = client.collections.list_all()

        # Get the keys and filter only our test collections
        collection_keys = list(collections.keys())
        test_collections = [k for k in collection_keys if k.startswith("SortingTestCollection")]

        # Verify they are in alphabetical order
        assert test_collections == sorted(test_collections)

        # Test with simple=False as well
        collections = client.collections.list_all(simple=False)
        collection_keys = list(collections.keys())
        test_collections = [k for k in collection_keys if k.startswith("SortingTestCollection")]
        assert test_collections == sorted(test_collections)

    finally:
        # Clean up
        client.collections.delete(
            ["SortingTestCollectionA", "SortingTestCollectionB", "SortingTestCollectionC"]
        )

from unittest.mock import MagicMock, patch

from weaviate.collections.classes.config_methods import (
    _collection_configs_from_json,
    _collection_configs_simple_from_json,
)


def test_collection_configs_from_json_sorting():
    """Test that _collection_configs_from_json returns collections sorted by key."""
    # Mock schema with collections in non-alphabetical order
    mock_schema = {
        "classes": [
            {"class": "CollectionC", "description": "Collection C"},
            {"class": "CollectionA", "description": "Collection A"},
            {"class": "CollectionB", "description": "Collection B"},
        ]
    }

    # Mock the _collection_config_from_json function to return a simple object
    with patch(
        "weaviate.collections.classes.config_methods._collection_config_from_json",
        return_value=MagicMock(),
    ):
        # Call the function
        result = _collection_configs_from_json(mock_schema)

        # Check that the keys are in alphabetical order
        assert list(result.keys()) == ["CollectionA", "CollectionB", "CollectionC"]


def test_collection_configs_simple_from_json_sorting():
    """Test that _collection_configs_simple_from_json returns collections sorted by key."""
    # Mock schema with collections in non-alphabetical order
    mock_schema = {
        "classes": [
            {"class": "CollectionC", "description": "Collection C"},
            {"class": "CollectionA", "description": "Collection A"},
            {"class": "CollectionB", "description": "Collection B"},
        ]
    }

    # Mock the _collection_config_simple_from_json function to return a simple object
    with patch(
        "weaviate.collections.classes.config_methods._collection_config_simple_from_json",
        return_value=MagicMock(),
    ):
        # Call the function
        result = _collection_configs_simple_from_json(mock_schema)

        # Check that the keys are in alphabetical order
        assert list(result.keys()) == ["CollectionA", "CollectionB", "CollectionC"]

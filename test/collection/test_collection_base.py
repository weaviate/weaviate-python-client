import pytest
from weaviate.collection.collection_base import _Config
from weaviate.connect import Connection


class MockConnection(Connection):
    def __init__(self):
        pass


def test_raises_error_when_accessing_config_when_no_config():
    config = _Config(MockConnection(), "mock")

    with pytest.raises(ValueError) as error:
        config.value
        assert (
            error
            == "Cannot access config.value as no collection configuration has been fetched yet. Make sure to only use the _Config class as a property of the Collection class."
        )

import uuid

import pytest

import weaviate


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    yield client
    client.schema.delete_all()


def test_add_data_object(client: weaviate.Client):
    """Test the `add_data_object` method"""

    assert sum(client.batch.shape) == 0
    assert client.batch.num_objects() == 0
    assert client.batch.is_empty_objects() is True

    client.batch.add_data_object(
        data_object={},
        class_name="Test",
    )
    assert client.batch.num_objects() == 1

    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        uuid=uuid.uuid4(),
    )
    assert client.batch.num_objects() == 2

    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        uuid=str(uuid.uuid4()),
    )
    assert client.batch.num_objects() == 3

    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        vector=[1, 2, 3],
    )
    assert client.batch.num_objects() == 4

    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        uuid=uuid.uuid4(),
        vector=[1, 2, 3],
    )
    assert client.batch.num_objects() == 5

    assert client.batch.is_empty_objects() is False

    client.batch.empty_objects()

    assert sum(client.batch.shape) == 0
    assert client.batch.num_objects() == 0
    assert client.batch.is_empty_objects() is True


def test_add_reference(client: weaviate.Client):
    """Test the `add_reference` method"""

    assert sum(client.batch.shape) == 0
    assert client.batch.num_references() == 0
    assert client.batch.is_empty_references() is True

    client.batch.add_reference(
        from_object_uuid=uuid.uuid4(),
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=uuid.uuid4(),
    )
    assert client.batch.num_references() == 1

    client.batch.add_reference(
        from_object_uuid=uuid.uuid4(),
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=str(uuid.uuid4()),
    )
    assert client.batch.num_references() == 2

    client.batch.add_reference(
        from_object_uuid=str(uuid.uuid4()),
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=uuid.uuid4(),
    )
    assert client.batch.num_references() == 3

    client.batch.add_reference(
        from_object_uuid=str(uuid.uuid4()),
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=str(uuid.uuid4()),
    )
    assert client.batch.num_references() == 4

    client.batch.add_reference(
        from_object_uuid=str(uuid.uuid4()),
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=str(uuid.uuid4()),
        to_object_class_name="Test2",
    )
    assert client.batch.num_references() == 5

    assert client.batch.is_empty_references() is False

    client.batch.empty_references()

    assert sum(client.batch.shape) == 0
    assert client.batch.num_references() == 0
    assert client.batch.is_empty_references() is True

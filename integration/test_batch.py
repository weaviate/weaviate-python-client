from dataclasses import dataclass
import uuid
from typing import Union, Sequence, Optional

import pytest

import weaviate


UUID = Union[str, uuid.UUID]


def has_batch_errors(results: dict) -> bool:
    """
    Check batch results for errors.

    Parameters
    ----------
    results : dict
        The Weaviate batch creation return value.
    """

    if results is not None:
        for result in results:
            if "result" in result and "errors" in result["result"]:
                if "error" in result["result"]["errors"]:
                    return True
    return False


@dataclass
class MockNumpyTorch:
    array: list

    def squeeze(self) -> "MockNumpyTorch":
        return self

    def tolist(self) -> list:
        return self.array


@dataclass
class MockTensorFlow:
    array: list

    def numpy(self) -> "MockNumpyTorch":
        return MockNumpyTorch(self.array)


@pytest.fixture(scope="function")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create_class(
        {
            "class": "Test",
            "properties": [{"name": "test", "dataType": ["Test"]}],
            "vectorizer": "none",
        }
    )
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uuid", [None, uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
def test_add_data_object(client: weaviate.Client, uuid: Optional[UUID], vector: Optional[Sequence]):
    """Test the `add_data_object` method"""
    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        uuid=uuid,
        vector=vector,
    )
    response = client.batch.create_objects()
    assert has_batch_errors(response) is False, str(response)


@pytest.mark.parametrize("from_object_uuid", [uuid.uuid4(), str(uuid.uuid4()), uuid.uuid4().hex])
@pytest.mark.parametrize("to_object_uuid", [uuid.uuid4().hex, uuid.uuid4(), str(uuid.uuid4())])
@pytest.mark.parametrize("to_object_class_name", [None, "Test"])
def test_add_reference(
    client: weaviate.Client,
    from_object_uuid: UUID,
    to_object_uuid: UUID,
    to_object_class_name: Optional[str],
):
    """Test the `add_reference` method"""

    # create the 2 objects first
    client.data_object.create(
        data_object={},
        class_name="Test",
        uuid=from_object_uuid,
    )
    client.data_object.create(
        data_object={},
        class_name="Test",
        uuid=to_object_uuid,
    )

    client.batch.add_reference(
        from_object_uuid=from_object_uuid,
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=to_object_uuid,
        to_object_class_name=to_object_class_name,
    )

    response = client.batch.create_references()
    assert has_batch_errors(response) is False, str(response)

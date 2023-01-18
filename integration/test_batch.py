from dataclasses import dataclass
import uuid
from typing import Union, Sequence, Optional

import pytest

import weaviate


UUID = Union[str, uuid.UUID]


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


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize(
    "vector",
    [None, [1, 2, 3], MockNumpyTorch([1, 2, 3]), MockTensorFlow([1, 2, 3])],
)
@pytest.mark.parametrize("uuid", [None, uuid.uuid4(), uuid.uuid4().hex, str(uuid.uuid4())])
def test_add_data_object(client: weaviate.Client, uuid: Optional[UUID], vector: Optional[Sequence]):
    """Test the `add_data_object` method"""
    client.batch.add_data_object(
        data_object={},
        class_name="Test",
        uuid=uuid,
        vector=vector,
    )


@pytest.mark.parametrize("from_object_uuid", [uuid.uuid4(), uuid.uuid4().hex, str(uuid.uuid4())])
@pytest.mark.parametrize("to_object_uuid", [uuid.uuid4(), uuid.uuid4().hex, str(uuid.uuid4())])
@pytest.mark.parametrize("to_object_class_name", [None, "Test2"])
def test_add_reference(
    client: weaviate.Client,
    from_object_uuid: UUID,
    to_object_uuid: UUID,
    to_object_class_name: Optional[str],
):
    """Test the `add_reference` method"""
    client.batch.add_reference(
        from_object_uuid=from_object_uuid,
        from_object_class_name="Test",
        from_property_name="test",
        to_object_uuid=to_object_uuid,
        to_object_class_name=to_object_class_name,
    )

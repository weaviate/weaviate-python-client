from typing import Generator
import pytest as pytest

import weaviate
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.util import parse_version_string


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local()
    if parse_version_string(client._connection._server_version) < parse_version_string("1.23"):
        pytest.skip("not implemented in this version")
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


def test_creating_blobs(client: weaviate.WeaviateClient) -> None:
    client.collections.delete("TestGeoPropsCreate")
    collection = client.collections.create(
        name="TestGeoPropsCreate",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="blob", data_type=DataType.BLOB)],
    )

    obj_uuid = collection.data.insert({"blob": "aGVsbG8gd29ybGQ="})

    obj = collection.query.fetch_object_by_id(obj_uuid)
    obj.metadata.creation_time.timestamp()

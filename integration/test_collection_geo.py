from typing import Generator
import pytest as pytest

import weaviate
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.collections.classes.types import GeoCoordinate
from weaviate.collections.classes.filters import Filter
from weaviate.util import parse_version_string


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local()
    if parse_version_string(client._connection._server_version) < parse_version_string("1.23"):
        pytest.skip("not implemented in this version")
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


def test_creating_geo_props(client: weaviate.WeaviateClient) -> None:
    client.collections.delete("TestGeoPropsCreate")
    collection = client.collections.create(
        name="TestGeoPropsCreate",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="geo", data_type=DataType.GEO_COORDINATES)],
    )

    obj_uuid = collection.data.insert({"geo": GeoCoordinate(latitude=1.0, longitude=1.0)})

    obj = collection.query.fetch_object_by_id(obj_uuid)
    assert obj is not None
    assert obj.properties["geo"] == GeoCoordinate(latitude=1.0, longitude=1.0)

    batch_ret = collection.data.insert_many([{"geo": GeoCoordinate(latitude=2.0, longitude=1.0)}])
    assert not batch_ret.has_errors

    obj_batch = collection.query.fetch_object_by_id(batch_ret.uuids[0])
    assert obj_batch is not None
    assert obj_batch.properties["geo"] == GeoCoordinate(latitude=2.0, longitude=1.0)

    # also accept dicts, but don't show that in the docs
    obj_uuid2 = collection.data.insert({"geo": {"latitude": 1.0, "longitude": 3.0}})
    obj2 = collection.query.fetch_object_by_id(obj_uuid2)
    assert obj2 is not None
    assert obj2.properties["geo"] == GeoCoordinate(latitude=1.0, longitude=3.0)

    batch_ret2 = collection.data.insert_many([{"geo": GeoCoordinate(latitude=3.0, longitude=1.0)}])
    assert not batch_ret2.has_errors

    obj_batch2 = collection.query.fetch_object_by_id(batch_ret2.uuids[0])
    assert obj_batch2 is not None
    assert obj_batch2.properties["geo"] == GeoCoordinate(latitude=3.0, longitude=1.0)


def test_geo_props_query(client: weaviate.WeaviateClient) -> None:
    client.collections.delete("TestGeoPropsQuery")
    collection = client.collections.create(
        name="TestGeoPropsQuery",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="geo", data_type=DataType.GEO_COORDINATES)],
    )

    collection.data.insert({"geo": GeoCoordinate(latitude=1.0, longitude=2.0)})

    objs = collection.query.fetch_objects()
    assert objs.objects[0].properties["geo"] == GeoCoordinate(latitude=1.0, longitude=2.0)


def test_geo_props_filter(client: weaviate.WeaviateClient) -> None:
    client.collections.delete("TestGeoPropsFilter")
    collection = client.collections.create(
        name="TestGeoPropsFilter",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="geo", data_type=DataType.GEO_COORDINATES)],
    )

    uuid1 = collection.data.insert({"geo": GeoCoordinate(latitude=1.0, longitude=2.0)})
    collection.data.insert({"geo": GeoCoordinate(latitude=1000.0, longitude=2.0)})
    objs = collection.query.fetch_objects(
        filters=Filter("geo").within_geo_range(
            GeoCoordinate(latitude=1.0, longitude=2.01), distance=5000.0
        ),
        return_properties=["geo"],
    )
    assert len(objs.objects) == 1
    assert objs.objects[0].uuid == uuid1
    assert objs.objects[0].properties["geo"] == GeoCoordinate(latitude=1.0, longitude=2.0)

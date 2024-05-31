import datetime
import uuid

import pytest

import weaviate
import weaviate.classes as wvc
from weaviate.collections.classes.config import DataType, Property

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")

DATE1 = datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


@pytest.mark.asyncio
async def test_fetch_objects_async() -> None:
    client = await weaviate.connect_to_local(use_async=True)
    name = "test_fetch_objects_async"
    await client.collections.delete(name)
    collection = await client.collections.create(
        name=name,
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            {"name": "John Doe"},
        ]
    )

    res = await collection.query.fetch_objects()
    assert len(res.objects) == 1
    assert res.objects[0].properties["name"] == "John Doe"
    await client.collections.delete(name)
    await client.close()


@pytest.mark.asyncio
async def test_config_add_reference() -> None:
    client = await weaviate.connect_to_local(use_async=True)
    name = "test_config_add_reference"
    await client.collections.delete(name)
    collection = await client.collections.create(
        name=name,
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    await collection.config.add_reference(
        wvc.config.ReferenceProperty(name="test", target_collection=collection.name)
    )
    await client.collections.delete(name)
    await client.close()

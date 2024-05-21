import datetime
import uuid

import pytest
import weaviate

from weaviate.collections.classes.config import (
    DataType,
    Property,
)

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")

DATE1 = datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


@pytest.mark.asyncio
async def test_fetch_objects_async() -> None:
    client = await weaviate.connect_to_local(use_async=True)
    await client.collections.delete_all()
    collection = await client.collections.create(
        name="test_fetch_objects_async",
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=weaviate.Configure.Vectorizer.none(),
    )
    await collection.data.insert_many(
        [
            {"name": "John Doe"},
        ]
    )

    res = await collection.query.fetch_objects()
    assert len(res.objects) == 1
    assert res.objects[0].properties["name"] == "John Doe"

import asyncio
from typing import List

import pytest
from .conftest import AsyncClientFactory

import weaviate.classes as wvc


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "objects,expected_errors",
    [
        ([{"name": "John Doe"}, {"name": "Jane Doe"}], 0),
        # ([{"name": "John Doe"}, {"firstName": "Jane", "lastName": "Doe"}], 1),
        # ([{"firstName": "John", "lastName": "Doe"}, {"firstName": "Jane", "lastName": "Doe"}], 2),
    ],
)
async def test_batch_stream(
    async_client_factory: AsyncClientFactory, objects: List[dict], expected_errors: int
) -> None:
    client = await async_client_factory()
    if client._connection._weaviate_version.is_lower_than(1, 30, 0):
        pytest.skip("Batch stream is only available in Weaviate 1.30.0 and higher")

    collection_name = "TestBatchStream"
    try:
        collection = await client.collections.create(
            name=collection_name,
            properties=[
                wvc.config.Property(name="name", data_type=wvc.config.DataType.TEXT),
            ],
        )

        async with client.stream as stream:
            for obj in objects:
                await stream.add_object(collection=collection_name, properties=obj)
        await asyncio.sleep(1)  # wait for the batch to be processed asynchronously
        assert len(client.stream.errors) == expected_errors
        res = await collection.aggregate.over_all()
        assert res.total_count == len(objects) - expected_errors
    finally:
        await client.collections.delete(collection_name)

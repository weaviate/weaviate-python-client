import pytest

from integration.conftest import AsyncCollectionFactory, CollectionFactory
from weaviate.classes.config import Configure, DataType, Property
from weaviate.classes.query import Filter
from weaviate.exceptions import WeaviateGenerativeQueryError, WeaviateQueryError


def test_generative_query_error(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_config=Configure.Generative.anyscale(),
    )
    collection.data.insert({"text": "hello"})

    with pytest.raises(WeaviateGenerativeQueryError) as generative_error:
        collection.generate.fetch_objects(single_prompt="Summarize {text}")
    assert isinstance(generative_error.value, WeaviateQueryError)
    assert "GRPC search" in str(generative_error.value)

    with pytest.raises(WeaviateQueryError) as query_error:
        collection.query.fetch_objects(filters=Filter.by_property("missing").equal(1))
    assert type(query_error.value) is WeaviateQueryError


@pytest.mark.asyncio
async def test_generative_query_error_async(
    async_collection_factory: AsyncCollectionFactory,
) -> None:
    collection = await async_collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        generative_config=Configure.Generative.anyscale(),
    )
    await collection.data.insert({"text": "hello"})

    with pytest.raises(WeaviateGenerativeQueryError) as generative_error:
        await collection.generate.fetch_objects(grouped_task="Summarize")
    assert isinstance(generative_error.value, WeaviateQueryError)
    assert "GRPC search" in str(generative_error.value)

    with pytest.raises(WeaviateQueryError) as query_error:
        await collection.query.fetch_objects(filters=Filter.by_property("missing").equal(1))
    assert type(query_error.value) is WeaviateQueryError

import json
import time

import pytest
import weaviate.classes as wvc

from .conftest import CollectionFactory, CollectionFactoryAsync, get_file_path

# download sphere dataset from https://weaviate.io/blog/sphere-dataset-in-weaviate#importing-sphere-with-python
# place file in profiling folder


def test_sphere_sync(collection_factory: CollectionFactory) -> None:
    sphere_file = get_file_path("sphere.1m.jsonl")

    collection = collection_factory(
        properties=[
            wvc.config.Property(name="url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="raw", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="sha", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        # headers={
        #     "X-Cohere-Api-Key": "YOUR_KEY",
        #     "X-OpenAI-Api-Key": "YOUR_KEY",
        # },
    )
    start = time.time()

    import_objects = 1000000
    with collection.batch.stream() as batch:
        with open(sphere_file) as jsonl_file:
            for i, jsonl in enumerate(jsonl_file):
                if i == import_objects:
                    break
                if batch.number_errors > 10:
                    print("Too many errors, stopping import")
                    break

                json_parsed = json.loads(jsonl)
                batch.add_object(
                    properties={
                        "url": json_parsed["url"],
                        "title": json_parsed["title"],
                        "raw": json_parsed["raw"],
                        "sha": json_parsed["sha"],
                    },
                    uuid=json_parsed["id"],
                    vector=json_parsed["vector"],
                )
                if i % 1000 == 0:
                    print(
                        f"Imported {len(collection)} objects after processing {i} lines in {time.time() - start} seconds"
                    )
    assert len(collection.batch.failed_objects) == 0
    assert len(collection) == import_objects
    print(f"Imported {import_objects} objects in {time.time() - start}")


@pytest.mark.asyncio
async def test_sphere_async(collection_factory_async: CollectionFactoryAsync) -> None:
    sphere_file = get_file_path("sphere.1m.jsonl")

    collection = await collection_factory_async(
        properties=[
            wvc.config.Property(name="url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="raw", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="sha", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        # headers={
        #     "X-Cohere-Api-Key": "YOUR_KEY",
        #     "X-OpenAI-Api-Key": "YOUR_KEY",
        # },
    )
    start = time.time()

    import_objects = 1000000
    async with collection.batch.stream() as batch:
        with open(sphere_file) as jsonl_file:
            for i, jsonl in enumerate(jsonl_file):
                if i == import_objects:
                    break
                if batch.number_errors > 10:
                    print("Too many errors, stopping import")
                    break

                json_parsed = json.loads(jsonl)
                await batch.add_object(
                    properties={
                        "url": json_parsed["url"],
                        "title": json_parsed["title"],
                        "raw": json_parsed["raw"],
                        "sha": json_parsed["sha"],
                    },
                    uuid=json_parsed["id"],
                    vector=json_parsed["vector"],
                )
                if i % 1000 == 0:
                    print(
                        f"Imported {await collection.length()} objects after processing {i} lines in {time.time() - start} seconds"
                    )
    assert len(collection.batch.failed_objects) == 0
    assert await collection.length() == import_objects
    print(f"Imported {import_objects} objects in {time.time() - start}")

import asyncio
import json
import time

import pytest
import weaviate
import weaviate.classes as wvc
from .conftest import get_file_path

# download sphere dataset from https://weaviate.io/blog/sphere-dataset-in-weaviate#importing-sphere-with-python
# place file in profiling folder


def test_stream_sync() -> None:
    sphere_file = get_file_path("sphere.1m.jsonl")
    collection_name = "SphereWithStream"
    with weaviate.connect_to_local() as client:
        client.collections.delete(collection_name)
        collection = client.collections.create(
            name=collection_name,
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

        import_objects = 100000
        with client.stream as stream:
            print("STARTING")
            with open(sphere_file) as jsonl_file:
                for i, jsonl in enumerate(jsonl_file):
                    if i == import_objects:
                        break

                    json_parsed = json.loads(jsonl)
                    stream.add_object(
                        collection=collection_name,
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
                        print(f"Imported {len(collection)} objects")
        assert len(collection) == import_objects
        print(f"Imported {import_objects} objects in {time.time() - start}")


@pytest.mark.asyncio
async def test_stream_async() -> None:
    sphere_file = get_file_path("sphere.1m.jsonl")
    collection_name = "SphereWithStream"
    async with weaviate.use_async_with_local() as client:
        await client.collections.delete(collection_name)
        collection = await client.collections.create(
            name=collection_name,
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

        import_objects = 100000
        async with client.stream as stream:
            print("STARTING")
            with open(sphere_file) as jsonl_file:
                for i, jsonl in enumerate(jsonl_file):
                    if i == import_objects:
                        break

                    json_parsed = json.loads(jsonl)
                    await stream.add_object(
                        collection=collection_name,
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
                        print(f"Imported {await collection.length()} objects")
        await asyncio.sleep(2)  # wait for the last batch to be processed
        assert await collection.length() == import_objects
        print(f"Imported {import_objects} objects in {time.time() - start}")


def test_batch() -> None:
    sphere_file = get_file_path("sphere.1m.jsonl")
    collection_name = "SphereWithStream"
    with weaviate.connect_to_local() as client:
        client.collections.delete(collection_name)
        collection = client.collections.create(
            name=collection_name,
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

        import_objects = 100000
        with client.batch.fixed_size(batch_size=1000, concurrent_requests=2) as batch:
            print("STARTING")
            with open(sphere_file) as jsonl_file:
                for i, jsonl in enumerate(jsonl_file):
                    if i == import_objects:
                        break

                    json_parsed = json.loads(jsonl)
                    batch.add_object(
                        collection=collection_name,
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
                        print(f"Imported {len(collection)} objects")
        assert len(collection) == import_objects
        print(f"Imported {import_objects} objects in {time.time() - start}")

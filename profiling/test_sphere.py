import json
import os
import time

import pytest

import weaviate
import weaviate.classes as wvc
from _pytest.fixtures import SubRequest

# download sphere dataset from https://weaviate.io/blog/sphere-dataset-in-weaviate#importing-sphere-with-python
# place file in profiling folder


def test_sphere_new(request: SubRequest) -> None:
    sphere_file = "sphere.100k.jsonl"
    if not os.path.exists(sphere_file) and not os.path.exists("profiling/" + sphere_file):
        pytest.skip("data does not exist")
    if os.path.exists("profiling/" + sphere_file):
        sphere_file = "profiling/" + sphere_file

    name = request.node.name

    client = weaviate.connect_to_local(
        # headers={
        #     "X-Cohere-Api-Key": "YOUR_KEY",
        #     "X-OpenAI-Api-Key": "YOUR_KEY",
        # },
    )
    client.collections.delete(name)
    client.collections.create(
        name=name,
        properties=[
            wvc.config.Property(name="url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="raw", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="sha", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
    )
    start = time.time()

    import_objects = 50000
    with client.batch.dynamic() as batch:
        with open(sphere_file) as jsonl_file:
            for i, jsonl in enumerate(jsonl_file):
                if i == import_objects or batch.number_errors > 10:
                    break

                json_parsed = json.loads(jsonl)
                batch.add_object(
                    collection=name,
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
                    print(f"Imported {i} objects")
    assert len(client.batch.failed_objects) == 0
    assert len(client.collections.get(name)) == import_objects
    client.collections.delete(name)
    print(f"{name}: Imported {import_objects} objects in {time.time() - start}")

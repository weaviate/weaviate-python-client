import json
import time

import weaviate.classes as wvc
from .conftest import get_file_path, CollectionFactory

# download sphere dataset from https://weaviate.io/blog/sphere-dataset-in-weaviate#importing-sphere-with-python
# place file in profiling folder


def test_sphere(collection_factory: CollectionFactory) -> None:
    sphere_file = get_file_path("sphere.100k.jsonl")

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

    import_objects = 50000
    with collection.batch.rate_limit(requests_per_minute=1234) as batch:
        with open(sphere_file) as jsonl_file:
            for i, jsonl in enumerate(jsonl_file):
                if i == import_objects or batch.number_errors > 10:
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
                    print(f"Imported {i} objects")
    assert len(collection.batch.failed_objects) == 0
    assert len(collection) == import_objects
    print(f"Imported {import_objects} objects in {time.time() - start}")

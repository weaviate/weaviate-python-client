import json
import time

import weaviate.classes as wvc

from .conftest import CollectionFactory, get_file_path

# download sphere dataset from https://weaviate.io/blog/sphere-dataset-in-weaviate#importing-sphere-with-python
# place file in profiling folder


def test_sphere(collection_factory: CollectionFactory) -> None:
    sphere_file = get_file_path("sphere.1m.jsonl")

    collection = collection_factory(
        properties=[
            wvc.config.Property(name="url", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="raw", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="sha", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        inverted_index_config=wvc.config.Configure.inverted_index(index_timestamps=True),
        replication_config=wvc.config.Configure.replication(
            factor=2,
            async_enabled=True,
            deletion_strategy=wvc.config.ReplicationDeletionStrategy.DELETE_ON_CONFLICT,
        ),
        
        # headers={
        #     "X-Cohere-Api-Key": "YOUR_KEY",
        #     "X-OpenAI-Api-Key": "YOUR_KEY",
        # },
    )
    start = time.time()

    # import_objects = 1000000
    import_objects = 400_000
    with collection.batch.dynamic() as batch:
        with open(sphere_file) as jsonl_file:
            for i, jsonl in enumerate(jsonl_file):
                if i == import_objects or batch.number_errors > 10:
                    break

                json_parsed = json.loads(jsonl)
                vector = json_parsed["vector"]
                for i in range(10):
                    batch.add_object(
                        properties={
                            "url": json_parsed["url"],
                            "title": json_parsed["title"] + str(i),
                            "raw": json_parsed["raw"] + str(i),
                            "sha": json_parsed["sha"],
                        },
                        # uuid=json_parsed["id"],
                        vector=shift_vector(vector, i),
                    )
                if i % 1000 == 0:
                    print(f"Imported {len(collection)} objects")
    assert len(collection.batch.failed_objects) == 0
    assert len(collection) == import_objects * 10
    print(f"Imported {import_objects} objects in {time.time() - start}")


def shift_vector(vector: list[float], shift: int) -> list[float]:
    shifted_vector: list[float] = []
    for i in range(len(vector)):
        shifted_vector.append(vector[(i + shift) % len(vector)])
    return shifted_vector
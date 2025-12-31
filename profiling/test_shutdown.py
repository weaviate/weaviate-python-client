import json
import random
import time
import weaviate
import weaviate.classes.config as wvcc


def setup(client: weaviate.WeaviateClient, collection: str) -> weaviate.collections.Collection:
    if client.collections.exists(collection):
        client.collections.delete(collection)
    return client.collections.create(
        name=collection,
        properties=[
            wvcc.Property(
                name="title",
                data_type=wvcc.DataType.TEXT,
            ),
            wvcc.Property(
                name="content",
                data_type=wvcc.DataType.TEXT,
            ),
        ],
        replication_config=wvcc.Configure.replication(factor=3, async_enabled=True),
        vector_config=wvcc.Configure.Vectors.self_provided(),
    )


def import_(client: weaviate.WeaviateClient, collection: str, how_many: int = 1_000_000) -> None:
    uuids: dict[str, int] = {}
    with client.batch.experimental(concurrency=1) as batch:
        for i in range(how_many):
            uuid = batch.add_object(
                collection=collection,
                properties={
                    "title": f"Title {i}",
                    "content": f"Content {i}",
                },
                vector=random_vector(),
            )
            uuids[str(uuid)] = i
            if batch.number_errors > 0:
                print(f"There are some errors {batch.number_errors}")

    for err in client.batch.failed_objects:
        print(err.message)
    assert len(client.batch.failed_objects) == 0, "Expected there to be no errors when importing"
    client.batch.wait_for_vector_indexing()
    with open("uuids.json", "w") as f:
        json.dump(uuids, f)


def verify(client: weaviate.WeaviateClient, collection: str, expected: int = 1_000_000) -> None:
    actual = 0
    count = 0
    c = client.collections.use(collection)
    while actual != expected:
        actual = len(c)
        print(f"Found {actual} objects, waiting for async repl to reach {expected}...")
        time.sleep(1)
        count += 1
        if count == 120:
            break
    assert actual == expected, f"Expected {expected} objects, found {actual}"


def random_vector() -> list[float]:
    return [random.uniform(0, 1) for _ in range(128)]


def test_main() -> None:
    collection = "BatchImportShutdownJourney"
    how_many = 500000
    with weaviate.connect_to_local() as client:
        collection = setup(client, collection)
        import_(client, collection.name, how_many)
        verify(client, collection.name, how_many)

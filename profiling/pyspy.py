import concurrent.futures
import math
from typing import List

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.data import DataObject
from weaviate.classes.query import MetadataQuery


def vector_search() -> None:
    client = weaviate.connect_to_local()

    name = "TestProfileVectorSearch"
    client.collections.delete(name)

    col = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        skip_argument_validation=True,
    )

    def shift_vector(i: int) -> List[float]:
        return [math.fmod(i * 0.1, 1) for i in range(i, i + 12)]

    _ret = col.data.insert_many([DataObject(vector=shift_vector(i) * 128) for i in range(12)])

    vector_search = [math.fmod(i * 0.1, 1) for i in range(12)] * 128
    for _ in range(10000):
        query_ret = col.query.near_vector(
            vector_search,
            limit=5,
            return_metadata=MetadataQuery(distance=True),
            return_properties=[],
        )
        assert query_ret.objects[0].uuid in _ret.uuids.values()

    client.close()


def multithreaded_queries() -> None:
    client = weaviate.connect_to_local()

    name = "TestProfileMultithreadedQueries"
    client.collections.delete(name)

    col = client.collections.create(
        name=name,
        properties=[
            Property(name="index", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    col = client.collections.get(name)

    col.data.insert_many([{"index": i} for i in range(1000)])

    def query_objects() -> None:
        for _ in range(100):
            objs = col.query.fetch_objects(
                limit=1000,
                include_vector=False,
                return_properties=["index"],
                return_metadata=None,
            )
            assert len(objs.objects) == 1000

    threads: List[concurrent.futures.Future] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        threads.extend([executor.submit(query_objects) for _ in range(4)])

    for thread in threads:
        thread.result()

    client.collections.delete(name)
    client.close()


multithreaded_queries()

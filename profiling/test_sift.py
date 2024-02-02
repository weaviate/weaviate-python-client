import time
from typing import List
import uuid

import h5py
from loguru import logger

import weaviate
import weaviate.classes as wvc

from _pytest.fixtures import SubRequest
from .conftest import get_file_path


def reset_schema(
    client: weaviate.WeaviateClient, name: str, efC: int, m: int, shards: int, distance: str
):
    client.collections.delete(name)
    vi = wvc.config.Configure.VectorIndex().hnsw(
        ef_construction=efC,
        max_connections=m,
        ef=-1,
        distance_metric=wvc.config.VectorDistances(distance),
    )

    client.collections.create(
        name=name,
        vectorizer_config=wvc.config.Configure.Vectorizer.none(),
        vector_index_config=vi,
        properties=[
            wvc.config.Property(
                name="i",
                data_type=wvc.config.DataType.INT,
            )
        ],
        inverted_index_config=wvc.config.Configure.inverted_index(index_timestamps=False),
        sharding_config=wvc.config.Configure.sharding(desired_count=shards),
    )


def load_records(client: weaviate.WeaviateClient, vectors: List[float], name: str):
    start = time.time()
    with client.batch.fixed_size(1000) as batch:
        for i, vector in enumerate(vectors):
            if i % 10000 == 0:
                logger.info(f"writing record {i}/{len(vectors)}. Took {time.time()-start}")

            data_object = {"i": i}

            batch.add_object(
                properties=data_object,
                vector=vector,
                collection=name,
                uuid=uuid.UUID(int=i),
            )

    logger.info(f"Finished writing {len(vectors)} records in {time.time()-start}s")


def test_sift(request: SubRequest) -> None:
    sift_file = get_file_path("sift-128-euclidean.hdf5")
    name = request.node.name

    f = h5py.File(sift_file)
    vectors = f["train"]

    client = weaviate.connect_to_local()

    reset_schema(client, name, 256, 32, 1, "l2-squared")
    load_records(client, vectors, name)

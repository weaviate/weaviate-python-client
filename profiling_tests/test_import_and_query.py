import time
import uuid
from typing import List

import h5py  # type: ignore
from _pytest.fixtures import SubRequest

import weaviate
import weaviate.classes as wvc
from weaviate.collections.collection import Collection

from .conftest import get_file_path

# The following code is used to test the performance of the weaviate client.
# Download the datasets at
#  - https://storage.googleapis.com/ann-datasets/ann-benchmarks/sift-128-euclidean.hdf5
#  - https://storage.googleapis.com/ann-datasets/ann-benchmarks/dbpedia-openai-1000k-angular.hdf5
#  and place it in the same folder as this file.
#
# In addition to weavaite, you will need to install the "h5py" package.
#
# To run all tests use `pytest -s test_sift.py` in the profiling directory. If you want to run only one of the tests
# you can use the `-k` flag, for example `pytest -s test_sift.py -k test_sift_v3`

EF_VALUES = [16, 32, 64, 128, 256, 512]
LIMIT = 10


def create_schema(
    client: weaviate.WeaviateClient, name: str, efC: int, m: int, shards: int, distance: str
) -> Collection:
    client.collections.delete(name)
    vi = wvc.config.Configure.VectorIndex.hnsw(
        ef_construction=efC,
        max_connections=m,
        ef=-1,
        distance_metric=wvc.config.VectorDistances(distance),
    )

    return client.collections.create(
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


def load_records_v4(collection: Collection, vectors: List[List[float]]) -> None:
    start = time.time()
    with collection.batch.fixed_size(1000) as batch:
        for i, vector in enumerate(vectors):
            data_object = {"i": i}

            batch.add_object(
                properties=data_object,
                vector=vector,
                uuid=uuid.UUID(int=i),
            )

    print(f"V4: Finished writing {len(vectors)} records in {time.time() - start}s")


def query_v4(
    collection: Collection, vectors: List[List[float]], neighbours: List[List[int]], ef: int
) -> None:
    collection.config.update(vector_index_config=wvc.config.Reconfigure.VectorIndex.hnsw(ef=ef))
    start = time.time()
    recall = 0.0

    for i, vec in enumerate(vectors):
        objs = collection.query.near_vector(
            near_vector=list(vec), limit=LIMIT, return_properties=[]
        ).objects
        ideal_neighbors = set(neighbours[i][:LIMIT])
        res_ids = [obj.uuid.int for obj in objs]
        recall += len(ideal_neighbors.intersection(res_ids)) / LIMIT

    print(
        f"V4: Querying {len(vectors)} records with ef {ef} in {time.time() - start}s with recall {recall / len(vectors)}"
    )


def run_v4(file: str, name: str, efc: int, m: int) -> None:
    sift_file = get_file_path(file)

    f = h5py.File(sift_file)
    vectors_import = f["train"]
    vectors_test = f["test"]
    ideal_neighbors = f["neighbors"]

    client = weaviate.connect_to_local()
    collection = create_schema(client, name, efc, m, 1, "l2-squared")
    load_records_v4(collection, vectors_import)
    for ef in EF_VALUES:
        query_v4(collection, vectors_test, ideal_neighbors, ef)


def test_sift_v4(request: SubRequest) -> None:
    run_v4(file="sift-128-euclidean.hdf5", name=request.node.name, efc=128, m=32)


def test_dbpedia_v4(request: SubRequest) -> None:
    run_v4(file="dbpedia-openai-1000k-angular.hdf5", name=request.node.name, efc=384, m=20)

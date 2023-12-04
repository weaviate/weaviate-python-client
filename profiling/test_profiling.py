# run:
# - profiling: pytest -m profiling profiling/test_profiling.py --profile-svg
# - benchmark: pytest profiling/test_profiling.py --benchmark-only --benchmark-disable-gc

from typing import Any, List
import pytest
import weaviate
from weaviate.collections.classes.config import Configure, DataType, Property


def are_floats_equal(num1: float, num2: float, decimal_places: int = 4) -> bool:
    # Use round to limit the precision to the desired decimal places
    rounded_num1 = round(num1, decimal_places)
    rounded_num2 = round(num2, decimal_places)
    if rounded_num1 != rounded_num2:
        print(f"{num1} != {num2}")

    return rounded_num1 == rounded_num2


def compare_float_lists(list1: List[float], list2: List[float], decimal_places: int = 4) -> bool:
    # Check if the lists have the same length
    if len(list1) != len(list2):
        return False

    # Compare each pair of elements up to the specified decimal place
    for num1, num2 in zip(list1, list2):
        if not are_floats_equal(num1, num2, decimal_places):
            return False

    return True


@pytest.fixture(scope="module")
def client() -> weaviate.WeaviateClient:
    client = weaviate.WeaviateClient(
        connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080", 50051),
        skip_init_checks=True,
    )
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


@pytest.mark.profiling
def test_get_vector(client: weaviate.WeaviateClient) -> None:
    name = "TestProfilingVector"
    col = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
    )

    col = client.collections.get(name)

    batchReturn = col.data.insert_many([{"Name": "Test" * (i % 10)} for i in range(1000)])
    assert len(batchReturn.uuids) == 1000

    obj = col.query.fetch_object_by_id(batchReturn.uuids[0], include_vector=True)
    assert obj is not None and obj.vector is not None

    for _ in range(100):
        objs = col.query.fetch_objects(
            limit=1000, include_vector=True, return_properties=None, return_metadata=None
        )
        assert len(objs.objects) == 1000
        assert objs.objects[0].vector is not None
        assert compare_float_lists(objs.objects[0].vector, obj.vector)

    client.collections.delete(name)


@pytest.mark.profiling
def test_get_float_properties(client: weaviate.WeaviateClient) -> None:
    name = "TestProfilingFloatProperties"
    client.collections.delete(name)

    col = client.collections.create(
        name=name,
        properties=[
            Property(name="Numbers", data_type=DataType.NUMBER_ARRAY),
            Property(name="index", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    col = client.collections.get(name)

    batchReturn = col.data.insert_many(
        [{"index": (i % 10 + 1), "numbers": [3.3] * (i % 10 + 1)} for i in range(1000)]
    )
    assert len(batchReturn.uuids) == 1000

    for _ in range(100):
        objs = col.query.fetch_objects(
            limit=1000,
            include_vector=False,
            return_properties=["numbers", "index"],
            return_metadata=None,
        )
        assert len(objs.objects) == 1000
        assert objs.objects[0].properties["numbers"] == [3.3] * int(
            objs.objects[0].properties["index"]
        )

    client.collections.delete(name)


def test_benchmark_get_vector(benchmark: Any, client: weaviate.WeaviateClient) -> None:
    benchmark(test_get_vector, client)


def test_benchmark_get_float_properties(benchmark: Any, client: weaviate.WeaviateClient) -> None:
    benchmark(test_get_float_properties, client)

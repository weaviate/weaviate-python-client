from typing import Dict, Generator, Optional, TypedDict, cast

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
)
from weaviate.collections.classes.data import (
    DataObject,
)
from weaviate.collections.classes.grpc import (
    MetadataQuery,
    METADATA,
    PROPERTIES,
)
from weaviate.collections.iterator import ITERATOR_CACHE_SIZE
from weaviate.exceptions import WeaviateInvalidInputError


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=False,
    )
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


class Data(TypedDict):
    data: int


@pytest.mark.parametrize(
    "include_vector",
    [False, True],
)
@pytest.mark.parametrize("return_metadata", [None, MetadataQuery.full()])
@pytest.mark.parametrize(
    "return_properties",
    [None, Data, ["data"]],
)
def test_iterator_arguments(
    collection_factory: CollectionFactory,
    include_vector: bool,
    return_metadata: Optional[METADATA],
    return_properties: Optional[PROPERTIES],
) -> None:
    collection = collection_factory(
        properties=[
            Property(name="data", data_type=DataType.INT),
            Property(name="text", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )

    collection.data.insert_many(
        [DataObject(properties={"data": i, "text": "hi"}) for i in range(10)]
    )

    iter_ = collection.iterator(
        include_vector, return_metadata=return_metadata, return_properties=return_properties
    )

    # Expect everything back
    if include_vector and return_properties is None and return_metadata == MetadataQuery.full():
        all_data: list[int] = sorted([cast(int, obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all("text" in obj.properties for obj in iter_)
        assert all("default" in obj.vector for obj in iter_)
        assert all(obj.metadata.creation_time is not None for obj in iter_)
        assert all(obj.metadata.score is not None for obj in iter_)
    # Expect everything back except vector
    elif (
        not include_vector and return_properties is None and return_metadata == MetadataQuery.full()
    ):
        all_data = sorted([cast(int, obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all("text" in obj.properties for obj in iter_)
        assert all("default" not in obj.vector for obj in iter_)
        assert all(obj.metadata.creation_time is not None for obj in iter_)
        assert all(obj.metadata.score is not None for obj in iter_)
    # Expect specified properties and vector
    elif include_vector and return_properties is not None:
        all_data = sorted([cast(int, obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all("text" not in obj.properties for obj in iter_)
        assert all("default" in obj.vector for obj in iter_)
        if return_metadata is not None:
            assert all(obj.metadata.creation_time is not None for obj in iter_)
            assert all(obj.metadata.score is not None for obj in iter_)
        else:
            assert all(obj.metadata._is_empty() for obj in iter_)
    # Expect specified properties and no vector
    elif not include_vector and return_properties is not None:
        all_data = sorted([cast(int, obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all("text" not in obj.properties for obj in iter_)
        assert all("default" not in obj.vector for obj in iter_)
        if return_metadata is not None:
            assert all(obj.metadata.creation_time is not None for obj in iter_)
            assert all(obj.metadata.score is not None for obj in iter_)
        else:
            assert all(obj.metadata._is_empty() for obj in iter_)


def test_iterator_dict_hint(collection_factory: CollectionFactory, request: SubRequest) -> None:
    collection = collection_factory(
        properties=[Property(name="data", data_type=DataType.INT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    collection.data.insert_many([DataObject(properties={"data": i}) for i in range(10)])

    with pytest.raises(WeaviateInvalidInputError) as e:
        for _ in collection.iterator(return_properties=dict):
            pass
    assert (
        "return_properties must only be a TypedDict or PROPERTIES within this context but is "
        in e.value.args[0]
    )


def test_iterator_with_default_generic(
    collection_factory: CollectionFactory, request: SubRequest
) -> None:
    class This(TypedDict):
        this: str

    class That(TypedDict):
        this: str
        that: str

    collection = collection_factory(
        properties=[
            Property(name="this", data_type=DataType.TEXT),
            Property(name="that", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        data_model_properties=That,
    )

    collection.data.insert_many(
        [DataObject(properties=That(this="this", that="that")) for _ in range(10)]
    )

    iter_ = collection.iterator()
    for this in iter_:
        assert this.properties["this"] == "this"
        assert this.properties["that"] == "that"

    iter__ = collection.iterator(return_properties=This)
    for that in iter__:
        assert that.properties["this"] == "this"
        assert "that" not in that.properties


@pytest.mark.parametrize(
    "count",
    [
        0,
        1,
        2,
        ITERATOR_CACHE_SIZE - 1,
        ITERATOR_CACHE_SIZE,
        ITERATOR_CACHE_SIZE + 1,
        2 * ITERATOR_CACHE_SIZE - 1,
        2 * ITERATOR_CACHE_SIZE,
        2 * ITERATOR_CACHE_SIZE + 1,
        20 * ITERATOR_CACHE_SIZE,
    ],
)
def test_iterator(collection_factory: CollectionFactory, count: int) -> None:
    collection = collection_factory(
        properties=[Property(name="data", data_type=DataType.INT)],
        vectorizer_config=Configure.Vectorizer.none(),
        data_model_properties=Dict[str, int],
    )

    if count > 0:
        collection.data.insert_many([DataObject(properties={"data": i}) for i in range(count)])

    expected = list(range(count))
    first_order = None

    # make sure a new iterator resets the internal state and that the return order is the same for every run
    for _ in range(3):
        # get the property and sort them - order returned by weaviate is not identical to the order inserted
        ret: list[int] = [obj.properties["data"] for obj in collection.iterator()]
        if first_order is None:
            first_order = ret
        else:
            assert first_order == ret

        assert sorted(ret) == expected

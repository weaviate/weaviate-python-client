import uuid
from typing import Any

import numpy as np
import pandas as pd
import polars as pl
import pytest

from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
)
from weaviate.collections.classes.grpc import (
    GroupBy,
    MetadataQuery,
)
from weaviate.exceptions import WeaviateInvalidInputError

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")
UUID2 = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
UUID3 = uuid.UUID("83d99755-9deb-4b16-8431-d1dff4ab0a75")


def test_near_vector(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.query.fetch_object_by_id(uuid_banana, include_vector=True)

    full_objects = collection.query.near_vector(
        banana.vector["default"], return_metadata=MetadataQuery(distance=True, certainty=True)
    ).objects
    assert len(full_objects) == 4

    objects_distance = collection.query.near_vector(
        banana.vector["default"], distance=full_objects[2].metadata.distance
    ).objects
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_vector(
        banana.vector["default"], certainty=full_objects[2].metadata.certainty
    ).objects
    assert len(objects_distance) == 3


def test_near_vector_limit(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.query.fetch_object_by_id(uuid_banana, include_vector=True)

    objs = collection.query.near_vector(banana.vector["default"], limit=2).objects
    assert len(objs) == 2


def test_near_vector_offset(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    uuid_fruit = collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.query.fetch_object_by_id(uuid_banana, include_vector=True)

    objs = collection.query.near_vector(banana.vector["default"], offset=1).objects
    assert len(objs) == 3
    assert objs[0].uuid == uuid_fruit


def test_near_vector_group_by_argument(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Count", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_banana1 = collection.data.insert({"Name": "Banana", "Count": 51})
    collection.data.insert({"Name": "Banana", "Count": 72})
    collection.data.insert({"Name": "car", "Count": 12})
    collection.data.insert({"Name": "Mountain", "Count": 1})

    banana1 = collection.query.fetch_object_by_id(uuid_banana1, include_vector=True)

    ret = collection.query.near_vector(
        banana1.vector["default"],
        group_by=GroupBy(
            prop="name",
            number_of_groups=4,
            objects_per_group=10,
        ),
        return_metadata=MetadataQuery(distance=True, certainty=True),
    )

    assert len(ret.objects) == 4
    assert ret.objects[0].belongs_to_group == "Banana"
    assert ret.objects[1].belongs_to_group == "Banana"
    assert ret.objects[2].belongs_to_group == "car"
    assert ret.objects[3].belongs_to_group == "Mountain"


@pytest.mark.parametrize(
    "near_vector", [[1, 0], [1.0, 0.0], np.array([1, 0]), pl.Series([1, 0]), pd.Series([1, 0])]
)
def test_near_vector_with_other_input(
    collection_factory: CollectionFactory, near_vector: Any
) -> None:
    collection = collection_factory(vectorizer_config=Configure.Vectorizer.none())

    uuid1 = collection.data.insert({}, vector=[1, 0])
    collection.data.insert({}, vector=[0, 1])

    ret = collection.query.near_vector(
        near_vector,
        distance=0.1,
    )
    assert len(ret.objects) == 1
    assert ret.objects[0].uuid == uuid1


@pytest.mark.parametrize(
    "near_vector",
    [
        {"first": [1, 0], "second": [1, 0, 0]},
        {"first": np.array([1, 0]), "second": [1, 0, 0]},
        {"first": pl.Series([1, 0]), "second": [1, 0, 0]},
        {"first": pd.Series([1, 0]), "second": [1, 0, 0]},
        {"first": [1.0, 0.0], "second": [1.0, 0.0, 0.0]},
    ],
)
def test_near_vector_with_named_vector_other_input(
    collection_factory: CollectionFactory, near_vector: Any
) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("Named vectors are supported in versions higher than 1.26.0")

    collection = collection_factory(
        vectorizer_config=[
            Configure.NamedVectors.none("first"),
            Configure.NamedVectors.none("second"),
        ]
    )

    uuid1 = collection.data.insert({}, vector={"first": [1, 0], "second": [1, 0, 0]})
    collection.data.insert({}, vector={"first": [0, 1], "second": [0, 0, 1]})

    ret = collection.query.near_vector(near_vector, distance=0.1, target_vector=["first", "second"])
    assert len(ret.objects) == 1
    assert ret.objects[0].uuid == uuid1


def test_near_vector_with_extra_vectors(collection_factory: CollectionFactory):
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("Named vectors are supported in versions higher than 1.26.0")

    collection = collection_factory(
        vectorizer_config=[
            Configure.NamedVectors.none("first"),
            Configure.NamedVectors.none("second"),
        ]
    )

    collection.data.insert({}, vector={"first": [1, 0], "second": [1, 0, 0]})
    with pytest.raises(WeaviateInvalidInputError):
        collection.query.near_vector(
            {"first": [1, 0], "second": [1, 0, 0]}, target_vector=["second"]
        )

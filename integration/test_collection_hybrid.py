import uuid
from typing import Any, List, Optional, Union

import numpy as np
import pandas as pd
import polars as pl
import pytest

import weaviate.classes as wvc
from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
)
from weaviate.collections.classes.grpc import (
    HybridFusion,
    GroupBy,
    MetadataQuery,
    NearVectorInputType,
    _HybridNearVector,
)
from weaviate.collections.classes.internal import Object
from weaviate.exceptions import (
    WeaviateInvalidInputError,
    WeaviateUnsupportedFeatureError,
)


@pytest.mark.parametrize("fusion_type", [HybridFusion.RANKED, HybridFusion.RELATIVE_SCORE])
def test_search_hybrid(collection_factory: CollectionFactory, fusion_type: HybridFusion) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    collection.data.insert({"Name": "some name"}, uuid=uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid=uuid.uuid4())
    objs = collection.query.hybrid(
        alpha=0, query="name", fusion_type=fusion_type, include_vector=True
    ).objects
    assert len(objs) == 1

    objs = collection.query.hybrid(
        alpha=1, query="name", fusion_type=fusion_type, vector=objs[0].vector["default"]
    ).objects
    assert len(objs) == 2


def test_search_hybrid_group_by(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    collection.data.insert({"Name": "some name"}, uuid=uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid=uuid.uuid4())
    if collection._connection.supports_groupby_in_bm25_and_hybrid():
        objs = collection.query.hybrid(
            alpha=0,
            query="name",
            include_vector=True,
            group_by=GroupBy(prop="name", objects_per_group=1, number_of_groups=2),
        ).objects
        assert len(objs) == 1
        assert objs[0].belongs_to_group == "some name"
    else:
        with pytest.raises(WeaviateUnsupportedFeatureError):
            collection.query.hybrid(
                alpha=0,
                query="name",
                include_vector=True,
                group_by=GroupBy(prop="name", objects_per_group=1, number_of_groups=2),
            )


@pytest.mark.parametrize("query", [None, ""])
def test_search_hybrid_only_vector(
    collection_factory: CollectionFactory, query: Optional[str]
) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_ = collection.data.insert({"Name": "some name"}, uuid=uuid.uuid4())
    vec = collection.query.fetch_object_by_id(uuid_, include_vector=True).vector
    assert vec is not None

    collection.data.insert({"Name": "other word"}, uuid=uuid.uuid4())

    objs = collection.query.hybrid(alpha=1, query=query, vector=vec["default"]).objects
    assert len(objs) == 2


@pytest.mark.parametrize("limit", [1, 2])
def test_hybrid_limit(collection_factory: CollectionFactory, limit: int) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    res = collection.data.insert_many(
        [
            {"Name": "test"},
            {"Name": "another"},
            {"Name": "test"},
        ]
    )
    assert res.has_errors is False
    assert len(collection.query.hybrid(query="test", alpha=0, limit=limit).objects) == limit


@pytest.mark.parametrize("offset,expected", [(0, 2), (1, 1), (2, 0)])
def test_hybrid_offset(collection_factory: CollectionFactory, offset: int, expected: int) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    res = collection.data.insert_many(
        [
            {"Name": "test"},
            {"Name": "another"},
            {"Name": "test"},
        ]
    )
    assert res.has_errors is False

    assert len(collection.query.hybrid(query="test", alpha=0, offset=offset).objects) == expected


def test_hybrid_alpha(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )

    res = collection.data.insert_many(
        [
            {"name": "banana"},
            {"name": "fruit"},
            {"name": "car"},
        ]
    )
    assert res.has_errors is False

    hybrid_res = collection.query.hybrid(query="fruit", alpha=0)
    bm25_res = collection.query.bm25(query="fruit")
    assert all(
        bm25_res.objects[i].uuid == hybrid_res.objects[i].uuid
        for i in range(len(hybrid_res.objects))
    )

    hybrid_res = collection.query.hybrid(query="fruit", alpha=1)
    text_res = collection.query.near_text(query="fruit")
    assert all(
        text_res.objects[i].uuid == hybrid_res.objects[i].uuid
        for i in range(len(hybrid_res.objects))
    )


def test_hybrid_near_vector_search(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_banana = collection.data.insert({"text": "banana"})
    obj = collection.query.fetch_object_by_id(uuid_banana, include_vector=True)

    if collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        with pytest.raises(WeaviateUnsupportedFeatureError):
            collection.query.hybrid(
                query=None,
                vector=wvc.query.HybridVector.near_vector(vector=obj.vector["default"]),
            ).objects
        return

    collection.data.insert({"text": "dog"})
    collection.data.insert({"text": "different concept"})

    hybrid_objs: List[Object[Any, Any]] = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_vector(vector=obj.vector["default"]),
    ).objects

    assert hybrid_objs[0].uuid == uuid_banana
    assert len(hybrid_objs) == 3

    # make a near vector search to get the distance
    near_vec = collection.query.near_vector(
        near_vector=obj.vector["default"], return_metadata=["distance"]
    ).objects
    assert near_vec[0].metadata.distance is not None

    hybrid_objs2 = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_vector(
            vector=obj.vector["default"], distance=near_vec[0].metadata.distance + 0.001
        ),
        return_metadata=MetadataQuery.full(),
    ).objects

    assert hybrid_objs2[0].uuid == uuid_banana
    assert len(hybrid_objs2) == 1


def test_hybrid_near_vector_search_named_vectors(collection_factory: CollectionFactory) -> None:
    dummy = collection_factory("dummy")
    collection_maker = lambda: collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="int", data_type=DataType.INT),
        ],
        vectorizer_config=[
            Configure.NamedVectors.text2vec_contextionary(
                name="text", vectorize_collection_name=False
            ),
            Configure.NamedVectors.text2vec_contextionary(
                name="int", vectorize_collection_name=False
            ),
        ],
    )

    if dummy._connection._weaviate_version.is_lower_than(1, 24, 0):
        with pytest.raises(WeaviateInvalidInputError):
            collection_maker()
        return

    collection = collection_maker()
    uuid_banana = collection.data.insert({"text": "banana"})
    collection.data.insert({"text": "dog"})
    collection.data.insert({"text": "different concept"})

    obj = collection.query.fetch_object_by_id(uuid_banana, include_vector=True)

    if collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        with pytest.raises(WeaviateUnsupportedFeatureError):
            hybrid_objs: List[Object[Any, Any]] = collection.query.hybrid(
                query=None,
                vector=wvc.query.HybridVector.near_vector(vector=obj.vector["text"]),
                target_vector="text",
            ).objects
        return

    hybrid_objs = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_vector(vector=obj.vector["text"]),
        target_vector="text",
    ).objects

    assert hybrid_objs[0].uuid == uuid_banana
    assert len(hybrid_objs) == 3

    # make a near vector search to get the distance
    near_vec = collection.query.near_vector(
        near_vector=obj.vector["text"], return_metadata=["distance"], target_vector="text"
    ).objects
    assert near_vec[0].metadata.distance is not None

    hybrid_objs2 = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_vector(
            vector=obj.vector["text"],
            distance=near_vec[0].metadata.distance + 0.001,
        ),
        target_vector="text",
        return_metadata=MetadataQuery.full(),
    ).objects

    assert hybrid_objs2[0].uuid == uuid_banana
    assert len(hybrid_objs2) == 1


def test_hybrid_near_text_search(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )

    if collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        with pytest.raises(WeaviateUnsupportedFeatureError):
            collection.query.hybrid(
                query=None,
                vector=wvc.query.HybridVector.near_text(query="banana pudding"),
            ).objects
        return

    uuid_banana_pudding = collection.data.insert({"text": "banana pudding"})
    collection.data.insert({"text": "banana smoothie"})
    collection.data.insert({"text": "different concept"})

    hybrid_objs: List[Object[Any, Any]] = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_text(query="banana pudding"),
    ).objects

    assert hybrid_objs[0].uuid == uuid_banana_pudding
    assert len(hybrid_objs) == 3

    hybrid_objs2 = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_text(
            query="banana",
            move_to=wvc.query.Move(concepts="pudding", force=0.1),
            move_away=wvc.query.Move(concepts="smoothie", force=0.1),
        ),
        return_metadata=MetadataQuery.full(),
    ).objects

    assert hybrid_objs2[0].uuid == uuid_banana_pudding


def test_hybrid_near_text_search_named_vectors(collection_factory: CollectionFactory) -> None:
    dummy = collection_factory("dummy")
    collection_maker = lambda: collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="int", data_type=DataType.INT),
        ],
        vectorizer_config=[
            Configure.NamedVectors.text2vec_contextionary(
                name="text", vectorize_collection_name=False
            ),
            Configure.NamedVectors.text2vec_contextionary(
                name="int", vectorize_collection_name=False
            ),
        ],
    )
    if dummy._connection._weaviate_version.is_lower_than(1, 24, 0):
        with pytest.raises(WeaviateInvalidInputError):
            collection_maker()
        return

    collection = collection_maker()
    uuid_banana_pudding = collection.data.insert({"text": "banana pudding"})
    collection.data.insert({"text": "banana smoothie"})
    collection.data.insert({"text": "different concept"})

    if collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        with pytest.raises(WeaviateUnsupportedFeatureError):
            hybrid_objs: List[Object[Any, Any]] = collection.query.hybrid(
                query=None,
                vector=wvc.query.HybridVector.near_text(query="banana pudding"),
                target_vector="text",
            ).objects
        return

    hybrid_objs = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_text(query="banana pudding"),
        target_vector="text",
    ).objects

    assert hybrid_objs[0].uuid == uuid_banana_pudding
    assert len(hybrid_objs) == 3

    hybrid_objs2 = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_text(
            query="banana",
            move_to=wvc.query.Move(concepts="pudding", force=0.1),
            move_away=wvc.query.Move(concepts="smoothie", force=0.1),
        ),
        target_vector="text",
        return_metadata=MetadataQuery.full(),
    ).objects

    assert hybrid_objs2[0].uuid == uuid_banana_pudding


@pytest.mark.parametrize(
    "vector",
    [
        {"first": [1, 0], "second": [1, 0, 0]},
        {"first": [1, 0], "second": np.array([1, 0, 0])},
        {"first": [1, 0], "second": pl.Series([1, 0, 0])},
        {"first": [1, 0], "second": pd.Series([1, 0, 0])},
    ],
)
def test_vector_per_target(
    collection_factory: CollectionFactory, vector: NearVectorInputType
) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("No multi target search below 1.26")

    collection = collection_factory(
        properties=[],
        vectorizer_config=[
            Configure.NamedVectors.none("first"),
            Configure.NamedVectors.none("second"),
        ],
    )

    uuid1 = collection.data.insert({}, vector={"first": [1, 0], "second": [1, 0, 0]})
    uuid2 = collection.data.insert({}, vector={"first": [0, 1], "second": [0, 0, 1]})

    objs = collection.query.hybrid(
        query=None,
        vector=vector,
        target_vector=["first", "second"],
    ).objects
    assert len(objs) == 2
    assert objs[0].uuid == uuid1
    assert objs[1].uuid == uuid2

    objs = collection.query.hybrid(
        query=None,
        vector=wvc.query.HybridVector.near_vector(vector, distance=0.1),
        target_vector=["first", "second"],
    ).objects
    assert len(objs) == 1
    assert objs[0].uuid == uuid1


@pytest.mark.parametrize(
    "near_vector,target_vector",
    [
        ({"first": [0, 1], "second": [[1, 0, 0], [0, 0, 1]]}, ["first", "second"]),
        ({"first": [[0, 1], [0, 1]], "second": [1, 0, 0]}, ["first", "second"]),
        (
            {"first": [[0, 1], [0, 1]], "second": [[1, 0, 0], [0, 0, 1]]},
            ["first", "second"],
        ),
        (
            wvc.query.HybridVector.near_vector({"first": [0, 1], "second": [[1, 0, 0], [0, 0, 1]]}),
            ["first", "second"],
        ),
        (
            wvc.query.HybridVector.near_vector({"first": [[0, 1], [0, 1]], "second": [1, 0, 0]}),
            ["first", "second"],
        ),
        (
            wvc.query.HybridVector.near_vector(
                {"first": [[0, 1], [0, 1]], "second": [[1, 0, 0], [0, 0, 1]]}
            ),
            ["first", "second"],
        ),
    ],
)
def test_same_target_vector_multiple_input_combinations(
    collection_factory: CollectionFactory,
    near_vector: Union[List[float], _HybridNearVector],
    target_vector: List[str],
) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 27, 0):
        pytest.skip("Multi vector per target is not supported in versions lower than 1.27.0")

    collection = collection_factory(
        properties=[],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none("first"),
            wvc.config.Configure.NamedVectors.none("second"),
        ],
    )

    uuid1 = collection.data.insert({}, vector={"first": [1, 0], "second": [0, 1, 0]})
    uuid2 = collection.data.insert({}, vector={"first": [0, 1], "second": [1, 0, 0]})

    objs = collection.query.hybrid(
        query=None,
        vector=near_vector,
        target_vector=target_vector,
        return_metadata=wvc.query.MetadataQuery.full(),
    ).objects
    assert sorted([obj.uuid for obj in objs]) == sorted([uuid2, uuid1])


def test_vector_distance(collection_factory: CollectionFactory):
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )

    if collection._connection._weaviate_version.is_lower_than(1, 26, 3):
        pytest.skip("Hybrid max vector distance is only supported in versions higher than 1.26.3")

    uuid1 = collection.data.insert({}, vector=[1, 0, 0])
    collection.data.insert({}, vector=[0, 1, 0])
    collection.data.insert({}, vector=[0, 0, 1])

    objs = collection.query.hybrid("name", vector=[1, 0, 0])
    assert len(objs.objects) == 3
    assert objs.objects[0].uuid == uuid1

    objs = collection.query.hybrid("name", vector=[1, 0, 0], max_vector_distance=0.1)
    assert len(objs.objects) == 1
    assert objs.objects[0].uuid == uuid1


def test_aggregate_max_vector_distance(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    if collection._connection._weaviate_version.is_lower_than(1, 26, 3):
        pytest.skip("Hybrid max vector distance is only supported in versions higher than 1.26.3")

    collection.data.insert({"name": "banana one"}, vector=[1, 0, 0, 0])
    collection.data.insert({"name": "banana two"}, vector=[0, 1, 0, 0])
    collection.data.insert({"name": "banana three"}, vector=[0, 1, 0, 0])
    collection.data.insert({"name": "banana four"}, vector=[1, 0, 0, 0])

    res = collection.aggregate.hybrid(
        "banana",
        vector=[1, 0, 0, 0],
        max_vector_distance=0.5,
        return_metrics=[wvc.aggregate.Metrics("name").text(count=True)],
    )
    assert res.total_count == 2

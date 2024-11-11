import uuid
from typing import List, Union, Dict, Sequence

import pytest

import weaviate.classes as wvc
from integration.conftest import CollectionFactory, OpenAICollection
from weaviate.collections.classes.aggregate import AggregateInteger
from weaviate.collections.classes.config import (
    PQConfig,
    _VectorIndexConfigHNSW,
    _VectorIndexConfigFlat,
    Vectorizers,
    ReferenceProperty,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.grpc import _MultiTargetVectorJoin
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.types import INCLUDE_VECTOR


def test_create_named_vectors_throws_error_in_old_version(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory("dummy")
    if not collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are supported in versions higher than 1.24.0")

    with pytest.raises(WeaviateInvalidInputError):
        collection_factory(
            properties=[
                wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
            ],
            vectorizer_config=[
                wvc.config.Configure.NamedVectors.text2vec_contextionary(
                    "title", source_properties=["title"], vectorize_collection_name=False
                ),
                wvc.config.Configure.NamedVectors.text2vec_contextionary(
                    name="content", source_properties=["content"], vectorize_collection_name=False
                ),
            ],
        )


@pytest.mark.parametrize(
    "include_vector",
    [["title", "content", "All", "AllExplicit", "bringYourOwn", "bringYourOwn2"], True],
)
def test_create_named_vectors(
    collection_factory: CollectionFactory, include_vector: Union[List[str], bool]
) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "title", source_properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                name="content", source_properties=["content"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                name="All", vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                name="AllExplicit",
                source_properties=["title", "content"],
                vectorize_collection_name=False,
            ),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn2"),
        ],
    )

    uuid = collection.data.insert(
        properties={"title": "Hello", "content": "World"},
        vector={
            "bringYourOwn": [0.5, 0.25, 0.75],
            "bringYourOwn2": [0.375, 0.625, 0.875],
        },
    )

    obj = collection.query.fetch_object_by_id(
        uuid,
        include_vector=include_vector,
    )
    assert obj.vector["title"] is not None
    assert obj.vector["content"] is not None
    assert obj.vector["All"] is not None
    assert obj.vector["bringYourOwn"] == [0.5, 0.25, 0.75]
    assert obj.vector["bringYourOwn2"] == [0.375, 0.625, 0.875]

    # vectorize different data so they must be different
    assert obj.vector["title"] != obj.vector["content"]
    assert obj.vector["title"] != obj.vector["All"]

    # vectorize same data so they must be the same
    assert obj.vector["AllExplicit"] == obj.vector["All"]


def test_insert_many_add(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "title", source_properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
        ],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(
                properties={"title": "Hello", "content": "World"},
                vector={"bringYourOwn": [0.5, 0.25, 0.75]},
            )
        ]
    )
    obj = collection.query.fetch_object_by_id(
        batch_return.uuids[0], include_vector=["title", "bringYourOwn"]
    )
    assert obj.vector["title"] is not None
    assert obj.vector["bringYourOwn"] == [0.5, 0.25, 0.75]


def test_update(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")

    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
        ],
    )

    uuid = collection.data.insert(
        properties={"title": "Hello", "content": "World"},
        vector={
            "bringYourOwn": [0.5, 0.25, 0.75],
        },
    )
    assert collection.query.fetch_object_by_id(uuid, include_vector=True).vector[
        "bringYourOwn"
    ] == [0.5, 0.25, 0.75]
    collection.data.update(
        uuid,
        vector={
            "bringYourOwn": [0.375, 0.625, 0.875],
        },
    )
    assert collection.query.fetch_object_by_id(uuid, include_vector=True).vector[
        "bringYourOwn"
    ] == [0.375, 0.625, 0.875]


def test_replace(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")

    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
        ],
    )

    uuid = collection.data.insert(
        properties={"title": "Hello", "content": "World"},
        vector={
            "bringYourOwn": [0.5, 0.25, 0.75],
        },
    )
    assert collection.query.fetch_object_by_id(uuid, include_vector=True).vector[
        "bringYourOwn"
    ] == [0.5, 0.25, 0.75]
    collection.data.replace(
        uuid,
        properties={"title": "Hello", "content": "World"},
        vector={
            "bringYourOwn": [0.375, 0.625, 0.875],
        },
    )
    assert collection.query.fetch_object_by_id(uuid, include_vector=True).vector[
        "bringYourOwn"
    ] == [0.375, 0.625, 0.875]


def test_query(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "title", source_properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                name="content", source_properties=["content"], vectorize_collection_name=False
            ),
        ],
    )

    uuid1 = collection.data.insert(
        properties={"title": "Hello", "content": "World"},
    )

    uuid2 = collection.data.insert(
        properties={"title": "World", "content": "Hello"},
    )

    objs = collection.query.near_text(query="Hello", target_vector="title", distance=0.1).objects
    assert objs[0].uuid == uuid1

    objs = collection.query.near_text(query="Hello", target_vector="content", distance=0.1).objects
    assert objs[0].uuid == uuid2


def test_generate(openai_collection: OpenAICollection) -> None:
    collection = openai_collection("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = openai_collection(
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_openai(
                "text", source_properties=["text"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.text2vec_openai(
                name="content", source_properties=["content"], vectorize_collection_name=False
            ),
        ],
    )

    uuid1 = collection.data.insert(
        properties={"text": "Hello", "content": "World"},
    )

    uuid2 = collection.data.insert(
        properties={"text": "World", "content": "Hello"},
    )

    objs = collection.generate.near_text(
        query="Hello",
        target_vector="text",
        return_metadata=["distance"],
        single_prompt="use {text} and {content} and combine them in a better order separated by whitespace",
        include_vector=["text", "content"],
    ).objects

    assert objs[0].uuid == uuid1
    assert objs[0].generated == "Hello World"

    objs = collection.generate.near_text(
        query="Hello",
        target_vector="content",
        distance=0.1,
        single_prompt="use {text} and {content} and combine them in a better order separated by whitespace",
    ).objects
    assert objs[0].uuid == uuid2
    assert objs[0].generated == "Hello World"


def test_batch_add(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "title", source_properties=["title"], vectorize_collection_name=False
            ),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn"),
        ],
    )
    uuid1 = uuid.uuid4()

    with collection.batch.dynamic() as batch:
        batch.add_object(
            properties={"title": "Hello", "content": "World"},
            vector={"bringYourOwn": [0.5, 0.25, 0.75]},
            uuid=uuid1,
        )

    obj = collection.query.fetch_object_by_id(uuid1, include_vector=["title", "bringYourOwn"])
    assert obj.vector["title"] is not None
    assert obj.vector["bringYourOwn"] == [0.5, 0.25, 0.75]


def test_named_vector_with_index_config(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="title", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="second", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "title",
                source_properties=["title"],
                vectorize_collection_name=False,
                vector_index_config=wvc.config.Configure.VectorIndex.flat(
                    distance_metric=wvc.config.VectorDistances.HAMMING,
                    quantizer=wvc.config.Configure.VectorIndex.Quantizer.bq(rescore_limit=10),
                ),
            ),
            wvc.config.Configure.NamedVectors.none(
                "custom",
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "default",
                vectorize_collection_name=False,  # needed as contextionary cant handle "_" in collection names
            ),
        ],
    )

    config = collection.config.get()

    assert config.vectorizer_config is None
    assert config.vectorizer is None
    assert config.vector_config is not None
    assert "title" in config.vector_config
    assert config.vector_config["title"].vectorizer.vectorizer == Vectorizers.TEXT2VEC_CONTEXTIONARY
    assert config.vector_config["title"].vectorizer.source_properties == ["title"]
    assert config.vector_config["title"].vectorizer.model == {"vectorizeClassName": False}
    assert config.vector_config["title"].vector_index_config is not None and isinstance(
        config.vector_config["title"].vector_index_config, _VectorIndexConfigFlat
    )
    assert (
        config.vector_config["title"].vector_index_config.distance_metric
        == wvc.config.VectorDistances.HAMMING
    )
    assert "custom" in config.vector_config
    assert config.vector_config["custom"].vectorizer.vectorizer == Vectorizers.NONE
    assert config.vector_config["custom"].vectorizer.source_properties is None
    assert config.vector_config["custom"].vectorizer.model == {}
    assert "default" in config.vector_config
    assert (
        config.vector_config["default"].vectorizer.vectorizer == Vectorizers.TEXT2VEC_CONTEXTIONARY
    )
    assert config.vector_config["default"].vectorizer.source_properties is None
    assert config.vector_config["default"].vectorizer.model == {"vectorizeClassName": False}


def test_aggregation(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="first", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="second", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="number", data_type=wvc.config.DataType.INT),
        ],
        # vectorizer_config=wvc.config.Configure.Vectorizer.text2vec_contextionary(vectorize_collection_name=False),
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "first",
                source_properties=["first"],
                vectorize_collection_name=False,
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "second",
                source_properties=["second"],
                vectorize_collection_name=False,
            ),
        ],
    )

    collection.data.insert(
        properties={"first": "Hello", "second": "World", "number": 1},
    )

    uuid2 = collection.data.insert(
        properties={"first": "World", "second": "Hello", "number": 2},
    )
    obj2 = collection.query.fetch_object_by_id(uuid2, include_vector=["second"])

    agg = collection.aggregate.near_text(
        "Hello",
        target_vector="first",
        object_limit=1,
        return_metrics=wvc.aggregate.Metrics("number").integer(),
    )
    assert isinstance(agg.properties["number"], AggregateInteger)
    assert agg.properties["number"].sum_ == 1
    assert agg.properties["number"].minimum == 1

    agg = collection.aggregate.near_vector(
        obj2.vector["second"],
        target_vector="second",
        object_limit=1,
        return_metrics=wvc.aggregate.Metrics("number").integer(),
    )
    assert isinstance(agg.properties["number"], AggregateInteger)
    assert agg.properties["number"].sum_ == 2
    assert agg.properties["number"].minimum == 2

    agg = collection.aggregate.near_object(
        obj2.uuid,
        target_vector="second",
        object_limit=1,
        return_metrics=wvc.aggregate.Metrics("number").integer(),
    )
    assert isinstance(agg.properties["number"], AggregateInteger)
    assert agg.properties["number"].sum_ == 2
    assert agg.properties["number"].minimum == 2

    agg = collection.aggregate.near_object(
        obj2.uuid,
        filters=wvc.query.Filter.by_property("number").equal(1),
        target_vector="second",
        object_limit=1,
        return_metrics=wvc.aggregate.Metrics("number").integer(),
    )
    assert isinstance(agg.properties["number"], AggregateInteger)
    assert agg.properties["number"].sum_ == 1
    assert agg.properties["number"].minimum == 1


def test_update_to_enable_quantizer_on_specific_named_vector(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    collection = collection_factory(
        properties=[
            wvc.config.Property(name="first", data_type=wvc.config.DataType.TEXT),
            wvc.config.Property(name="second", data_type=wvc.config.DataType.TEXT),
        ],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "first",
                source_properties=["first"],
                vectorize_collection_name=False,
            ),
            wvc.config.Configure.NamedVectors.text2vec_contextionary(
                "second",
                source_properties=["second"],
                vectorize_collection_name=False,
            ),
        ],
    )
    config = collection.config.get()
    assert config.vector_config is not None
    assert config.vector_config["first"].vector_index_config is not None
    assert config.vector_config["second"].vector_index_config is not None
    assert isinstance(config.vector_config["second"].vector_index_config, _VectorIndexConfigHNSW)
    assert config.vector_config["second"].vector_index_config.quantizer is None

    collection.config.update(
        vectorizer_config=[
            wvc.config.Reconfigure.NamedVectors.update(
                name="second",
                vector_index_config=wvc.config.Reconfigure.VectorIndex.hnsw(
                    quantizer=wvc.config.Reconfigure.VectorIndex.Quantizer.pq()
                ),
            )
        ]
    )
    config = collection.config.get()
    assert config.vector_config is not None
    assert config.vector_config["first"].vector_index_config is not None
    assert config.vector_config["second"].vector_index_config is not None
    assert isinstance(config.vector_config["second"].vector_index_config, _VectorIndexConfigHNSW)
    assert isinstance(config.vector_config["second"].vector_index_config.quantizer, PQConfig)
    assert config.vector_config["second"].vector_index_config.quantizer.centroids == 256


# def test_update_to_change_quantizer_from_pq_to_bq_on_specific_named_vector(
#     collection_factory: CollectionFactory,
# ) -> None:
#     collection = collection_factory("dummy")
#     if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
#         pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
#     collection = collection_factory(
#         properties=[
#             wvc.config.Property(name="first", data_type=wvc.config.DataType.TEXT),
#             wvc.config.Property(name="second", data_type=wvc.config.DataType.TEXT),
#         ],
#         vectorizer_config=[
#             wvc.config.Configure.NamedVectors.text2vec_contextionary(
#                 "first",
#                 source_properties=["first"],
#                 vectorize_collection_name=False,
#             ),
#             wvc.config.Configure.NamedVectors.text2vec_contextionary(
#                 "second",
#                 source_properties=["second"],
#                 vectorize_collection_name=False,
#                 vector_index_config=wvc.config.Configure.VectorIndex.hnsw(
#                     quantizer=wvc.config.Configure.VectorIndex.Quantizer.pq()
#                 ),
#             ),
#         ],
#     )

#     config = collection.config.get()
#     assert config.vector_config is not None
#     assert config.vector_config["first"].vector_index_config is not None
#     assert config.vector_config["second"].vector_index_config is not None
#     assert isinstance(config.vector_config["second"].vector_index_config.quantizer, PQConfig)

#     with pytest.raises(WeaviateInvalidInputError):
#         collection.config.update(
#             vectorizer_config=[
#                 wvc.config.Reconfigure.NamedVectors.update(
#                     name="second",
#                     vector_index_config=wvc.config.Reconfigure.VectorIndex.hnsw(
#                         quantizer=wvc.config.Reconfigure.VectorIndex.Quantizer.bq()
#                     ),
#                 )
#             ]
#         )


def test_duplicate_named_vectors(collection_factory: CollectionFactory) -> None:
    collection = collection_factory("dummy")
    if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")
    with pytest.raises(WeaviateInvalidInputError) as e:
        collection_factory(
            vectorizer_config=[
                wvc.config.Configure.NamedVectors.text2vec_contextionary(
                    "title", source_properties=["title"], vectorize_collection_name=False
                ),
                wvc.config.Configure.NamedVectors.text2vec_contextionary(
                    "title", source_properties=["content"], vectorize_collection_name=False
                ),
            ],
        )
        assert "Vector config names must be unique. Found duplicates" in str(e)


@pytest.mark.parametrize(
    "target_vector",
    [
        ["first", "second"],
        wvc.query.TargetVectors.sum(["first", "second"]),
        wvc.query.TargetVectors.minimum(["first", "second"]),
        wvc.query.TargetVectors.average(["first", "second"]),
        wvc.query.TargetVectors.manual_weights({"first": 1.2, "second": 0.7}),
        wvc.query.TargetVectors.relative_score({"first": 1.2, "second": 0.7}),
    ],
)
def test_named_vector_multi_target(
    collection_factory: CollectionFactory, target_vector: Union[List[str], _MultiTargetVectorJoin]
) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.26.0")

    collection = collection_factory(
        properties=[],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none("first"),
            wvc.config.Configure.NamedVectors.none("second"),
        ],
    )

    uuid1 = collection.data.insert({}, vector={"first": [1, 0, 0], "second": [0, 1, 0]})
    uuid2 = collection.data.insert({}, vector={"first": [0, 1, 0], "second": [1, 0, 0]})

    objs = collection.query.near_vector([1.0, 0.0, 0.0], target_vector=target_vector).objects
    assert sorted([obj.uuid for obj in objs]) == sorted([uuid1, uuid2])  # order is not guaranteed


def test_named_vector_multi_target_vector_per_target(collection_factory: CollectionFactory) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.26.0")

    collection = collection_factory(
        properties=[],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none("first"),
            wvc.config.Configure.NamedVectors.none("second"),
        ],
    )

    uuid1 = collection.data.insert({}, vector={"first": [1, 0], "second": [0, 1, 0]})
    uuid2 = collection.data.insert({}, vector={"first": [0, 1], "second": [1, 0, 0]})

    objs = collection.query.near_vector(
        {"first": [1.0, 0.0], "second": [1.0, 0.0, 0.0]}, target_vector=["first", "second"]
    ).objects
    assert sorted([obj.uuid for obj in objs]) == sorted([uuid1, uuid2])  # order is not guaranteed


def test_multi_query_error_no_target_vector(collection_factory: CollectionFactory) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.26.0")

    collection = collection_factory(
        properties=[],
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none("first"),
            wvc.config.Configure.NamedVectors.none("second"),
        ],
    )

    with pytest.raises(WeaviateInvalidInputError):
        collection.query.near_vector([[1.0, 0.0], [1.0, 0.0, 0.0]])

    with pytest.raises(WeaviateInvalidInputError):
        collection.query.near_vector({"first": [1.0, 0.0], "second": [1.0, 0.0, 0.0]})

    with pytest.raises(WeaviateInvalidInputError):
        collection.query.near_vector({"first": [[1.0, 0.0], [1.0, 0.0]], "second": [1.0, 0.0, 0.0]})

    with pytest.raises(WeaviateInvalidInputError):
        collection.query.near_vector([[[1.0, 0.0], [1.0, 0.0]], [1.0, 0.0, 0.0]])


@pytest.mark.parametrize(
    "target_vector, distances",
    [
        (wvc.query.TargetVectors.sum(["first", "second"]), [1, 3]),
        (wvc.query.TargetVectors.manual_weights({"first": 1, "second": [1, 1]}), [1, 3]),
        (wvc.query.TargetVectors.manual_weights({"first": 1, "second": [1, 2]}), [2, 4]),
        (
            wvc.query.TargetVectors.manual_weights({"second": [1, 2], "first": 1}),
            [2, 4],
        ),  # different order
    ],
)
def test_same_target_vector_multiple_input(
    collection_factory: CollectionFactory,
    target_vector: Union[List[str], _MultiTargetVectorJoin],
    distances: List[float],
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

    objs = collection.query.near_vector(
        {"first": [0.0, 1.0], "second": [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]},
        target_vector=target_vector,
        return_metadata=wvc.query.MetadataQuery.full(),
    ).objects
    assert [obj.uuid for obj in objs] == [uuid2, uuid1]
    assert objs[0].metadata.distance == distances[0]
    assert objs[1].metadata.distance == distances[1]


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
            {"first": [[0, 1], [0, 1]], "second": [[1, 0, 0], [0, 0, 1]]},
            ["second", "first"],  # different order
        ),
    ],
)
def test_same_target_vector_multiple_input_combinations(
    collection_factory: CollectionFactory,
    near_vector: Dict[str, Union[Sequence[float], Sequence[Sequence[float]]]],
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

    objs = collection.query.near_vector(
        near_vector, target_vector=target_vector, return_metadata=wvc.query.MetadataQuery.full()
    ).objects
    assert sorted([obj.uuid for obj in objs]) == sorted([uuid2, uuid1])


def test_deprecated_syntax(collection_factory: CollectionFactory):
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

    collection.data.insert({}, vector={"first": [1, 0], "second": [0, 1, 0]})
    collection.data.insert({}, vector={"first": [0, 1], "second": [1, 0, 0]})

    with pytest.raises(WeaviateInvalidInputError) as e:
        collection.query.near_vector(
            [[0.0, 1.0], [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]],
            target_vector=["first", "second", "second"],
            return_metadata=wvc.query.MetadataQuery.full(),
        )
    assert "Providing lists of lists has been deprecated" in str(e)

    with pytest.raises(WeaviateInvalidInputError) as e:
        collection.query.near_vector(
            [[0.0, 1.0], [1.0, 0.0, 0.0]],
            target_vector=["first", "second"],
            return_metadata=wvc.query.MetadataQuery.full(),
        )
    assert "Providing lists of lists has been deprecated" in str(e)


@pytest.mark.parametrize(
    "include_vector, expected",
    [
        (False, {}),
        (["bringYourOwn1"], {"bringYourOwn1": [0, 1, 2]}),
        # TODO: to be uncommented when https://github.com/weaviate/weaviate/issues/6279 is resolved
        # (True, {"bringYourOwn1": [0, 1, 2], "bringYourOwn2": [3, 4, 5]})
    ],
)
def test_include_vector_on_references(
    collection_factory: CollectionFactory, include_vector: INCLUDE_VECTOR, expected: dict
) -> None:
    """Test include vector on reference"""
    dummy = collection_factory()
    if dummy._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectorizers are only supported in Weaviate v1.24.0 and higher.")

    ref_collection = collection_factory(
        name="Target",
        vectorizer_config=[
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn1"),
            wvc.config.Configure.NamedVectors.none(name="bringYourOwn2"),
        ],
    )

    TO_UUID = ref_collection.data.insert(
        properties={}, vector={"bringYourOwn1": [0, 1, 2], "bringYourOwn2": [3, 4, 5]}
    )

    collection = collection_factory(
        name="Source",
        references=[ReferenceProperty(name="hasRef", target_collection=ref_collection.name)],
    )

    collection.data.insert({}, references={"hasRef": TO_UUID})

    objs = collection.query.fetch_objects(
        return_references=wvc.query.QueryReference(link_on="hasRef", include_vector=include_vector)
    ).objects

    assert objs[0].references["hasRef"].objects[0].vector == expected

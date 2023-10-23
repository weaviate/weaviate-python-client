import pathlib

import pytest

import weaviate
from weaviate.collection.classes.aggregate import Metrics
from weaviate.collection.classes.config import DataType, Property, ReferenceProperty, ConfigFactory
from weaviate.util import file_encoder_b64


@pytest.fixture(scope="module")
def client():
    connection_params = weaviate.ConnectionParams.from_url(
        url="http://localhost:8080", grpc_port=50051
    )
    client = weaviate.WeaviateClient(connection_params)
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


def test_simple_aggregation(client: weaviate.WeaviateClient):
    name = "TestSimpleAggregation"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name, properties=[Property(name="text", data_type=DataType.TEXT)]
    )
    collection.data.insert({"text": "some text"})
    res = collection.aggregate.over_all(
        return_metrics=[Metrics("text", DataType.TEXT).returning(count=True)]
    )
    assert res.properties["text"].count == 1


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
    ],
)
def test_near_object_aggregation(client: weaviate.WeaviateClient, option: dict, expected_len: int):
    name = "TestNearObjectAggregation"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=ConfigFactory.Vectorizer.text2vec_contextionary(
            vectorize_class_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    res = collection.aggregate.near_object(
        uuid,
        return_metrics=[
            Metrics("text", DataType.TEXT).returning(
                count=True, top_occurrences_count=True, top_occurrences_value=True
            )
        ],
        **option
    )
    assert res.properties["text"].count == expected_len
    assert len(res.properties["text"].top_occurrences) == expected_len
    assert text_1 in [
        top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
    ]
    if expected_len == 2:
        assert text_2 in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]
    else:
        assert text_2 not in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
    ],
)
def test_near_vector_aggregation(client: weaviate.WeaviateClient, option: dict, expected_len: int):
    name = "TestNearVectorAggregation"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=ConfigFactory.Vectorizer.text2vec_contextionary(
            vectorize_class_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    collection.data.insert({"text": text_2})
    res = collection.aggregate.near_vector(
        obj.metadata.vector,
        return_metrics=[
            Metrics("text", DataType.TEXT).returning(
                count=True, top_occurrences_count=True, top_occurrences_value=True
            )
        ],
        **option
    )
    assert res.properties["text"].count == expected_len
    assert len(res.properties["text"].top_occurrences) == expected_len
    assert text_1 in [
        top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
    ]
    if expected_len == 2:
        assert text_2 in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]
    else:
        assert text_2 not in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
    ],
)
def test_near_text_aggregation(client: weaviate.WeaviateClient, option: dict, expected_len: int):
    name = "TestNearTextAggregation"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=ConfigFactory.Vectorizer.text2vec_contextionary(
            vectorize_class_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    res = collection.aggregate.near_text(
        text_1,
        return_metrics=[
            Metrics("text", DataType.TEXT).returning(
                count=True, top_occurrences_count=True, top_occurrences_value=True
            )
        ],
        **option
    )
    assert res.properties["text"].count == expected_len
    assert len(res.properties["text"].top_occurrences) == expected_len
    assert text_1 in [
        top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
    ]
    if expected_len == 2:
        assert text_2 in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]
    else:
        assert text_2 not in [
            top_occurrence.value for top_occurrence in res.properties["text"].top_occurrences
        ]


@pytest.mark.parametrize("option", [{"object_limit": 1}, {"certainty": 0.9}, {"distance": 0.1}])
def test_near_image_aggregation(client: weaviate.WeaviateClient, option: dict):
    name = "TestNearImageAggregation"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="rating", data_type=DataType.INT),
            Property(name="image", data_type=DataType.BLOB),
        ],
        vectorizer_config=ConfigFactory.Vectorizer.img2vec_neural(image_fields=["image"]),
    )
    img_path = pathlib.Path("integration/weaviate-logo.png")
    collection.data.insert({"image": file_encoder_b64(img_path), "rating": 9})
    res = collection.aggregate.near_image(
        img_path,
        return_metrics=[Metrics("rating", DataType.INT).returning(count=True, maximum=True)],
        **option
    )
    assert res.properties["rating"].count == 1
    assert res.properties["rating"].maximum == 9


def test_group_by_aggregation(client: weaviate.WeaviateClient):
    name = "TestGroupByAggregation"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="int", data_type=DataType.INT),
        ],
    )
    collection.data.insert({"text": "some text", "int": 1})
    collection.data.insert({"text": "some text", "int": 2})

    res = collection.aggregate_group_by.over_all(
        "text",
        return_metrics=[
            Metrics("text", DataType.TEXT).returning(count=True),
            Metrics("int", DataType.INT).returning(count=True),
        ],
    )
    assert len(res) == 1
    assert res[0].grouped_by.prop == "text"
    assert res[0].grouped_by.value == "some text"
    assert res[0].properties["text"].count == 2
    assert res[0].properties["int"].count == 2

    res = collection.aggregate_group_by.over_all(
        "int",
        return_metrics=[
            Metrics("text", DataType.TEXT).returning(count=True),
            Metrics("int", DataType.INT).returning(count=True),
        ],
    )
    assert len(res) == 2
    assert res[0].grouped_by.prop == "int"
    assert res[0].grouped_by.value == "1" or res[1].grouped_by.value == "1"
    assert res[0].properties["text"].count == 1
    assert res[0].properties["int"].count == 1
    assert res[1].grouped_by.prop == "int"
    assert res[1].grouped_by.value == "2" or res[0].grouped_by.value == "2"
    assert res[1].properties["text"].count == 1
    assert res[1].properties["int"].count == 1


@pytest.mark.skip(reason="Validation logic is not robust enough currently")
def test_mistake_in_usage(client: weaviate.WeaviateClient):
    collection = client.collection.get("TestMistakeInUsage")
    with pytest.raises(TypeError) as e:
        collection.aggregate.over_all([Metrics("text", DataType.TEXT)])
    assert (
        e.value.args[0]
        == "One of the aggregations is an unexpected type: <class 'weaviate.collection.classes.aggregate.Metrics'>. Did you forget to append .returning() to .with_()?"
    )
    with pytest.raises(TypeError) as e:
        collection.aggregate.over_all(aggregations=[Metrics("text", DataType.TEXT)])
    assert (
        e.value.args[0]
        == "One of the aggregations is an unexpected type: <class 'weaviate.collection.classes.aggregate.Metrics'>. Did you forget to append .returning() to .with_()?"
    )


def test_all_available_aggregations(client: weaviate.WeaviateClient):
    name = "TestAllAvailableAggregations"
    client.collection.delete(name)
    collection = client.collection.create(
        name=name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(
                name="texts",
                data_type=DataType.TEXT_ARRAY,
            ),
            Property(name="int", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="float", data_type=DataType.NUMBER),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="bool", data_type=DataType.BOOL),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="date", data_type=DataType.DATE),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
            ReferenceProperty(name="ref", target_collection="TestAllAvailableAggregations"),
        ],
    )
    collection.data.insert(
        {
            "text": "some text",
            "texts": ["some text", "some more text"],
            "int": 1,
            "ints": [1, 2],
            "float": 1.0,
            "floats": [1.0, 2.0],
            "bool": True,
            "bools": [True, False],
            "date": "2021-01-01T00:00:00Z",
            "dates": ["2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z"],
        }
    )
    res = collection.aggregate.over_all(
        return_metrics=[
            Metrics("text", DataType.TEXT).returning(count=True),
            Metrics("texts", DataType.TEXT_ARRAY).returning(count=True),
            Metrics("int", DataType.INT).returning(count=True),
            Metrics("ints", DataType.INT_ARRAY).returning(count=True),
            Metrics("float", DataType.NUMBER).returning(count=True),
            Metrics("floats", DataType.NUMBER_ARRAY).returning(count=True),
            Metrics("bool", DataType.BOOL).returning(count=True),
            Metrics("bools", DataType.BOOL_ARRAY).returning(count=True),
            Metrics("date", DataType.DATE).returning(count=True),
            Metrics("dates", DataType.DATE_ARRAY).returning(count=True),
        ]
    )
    assert res.properties["text"].count == 1
    assert res.properties["texts"].count == 2
    assert res.properties["int"].count == 1
    assert res.properties["ints"].count == 2
    assert res.properties["float"].count == 1
    assert res.properties["floats"].count == 2
    assert res.properties["bool"].count == 1
    assert res.properties["bools"].count == 2
    assert res.properties["date"].count == 1
    assert res.properties["dates"].count == 2

import pathlib
import uuid
from datetime import datetime, timezone

import pytest
from _pytest.fixtures import SubRequest

from integration.conftest import CollectionFactory, CollectionFactoryGet
from weaviate.collections.classes.aggregate import (
    AggregateBoolean,
    AggregateDate,
    AggregateInteger,
    AggregateNumber,
    AggregateText,
    AggregateReturn,
    Metrics,
    GroupByAggregate,
)
from weaviate.collections.classes.config import DataType, Property, ReferenceProperty, Configure
from weaviate.collections.classes.filters import Filter, _Filters
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateQueryError
from weaviate.util import file_encoder_b64

from weaviate.collections.classes.grpc import Move

from weaviate.collections.classes.tenants import Tenant

UUID1 = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
UUID2 = uuid.UUID("577887c1-4c6b-5594-aa62-f0c17883d9cf")


@pytest.mark.parametrize("how_many", [1, 10000, 20000, 20001, 100000])
def test_collection_length(collection_factory: CollectionFactory, how_many: int) -> None:
    """Uses .aggregate behind-the-scenes"""
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many([{} for _ in range(how_many)])
    assert len(collection) == how_many


@pytest.mark.parametrize("how_many", [1, 10000, 20000, 20001, 100000])
def test_collection_length_tenant(collection_factory: CollectionFactory, how_many: int) -> None:
    """Uses .aggregate behind-the-scenes"""
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create(
        tenants=[Tenant(name="tenant1"), Tenant(name="tenant2"), Tenant(name="tenant3")]
    )
    collection.with_tenant("tenant1").data.insert_many([{} for _ in range(how_many)])
    collection.with_tenant("tenant2").data.insert_many([{} for _ in range(how_many * 2)])

    assert len(collection.with_tenant("tenant2")) == how_many * 2
    assert len(collection.with_tenant("tenant3")) == 0


def test_empty_aggregation(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(properties=[Property(name="text", data_type=DataType.TEXT)])
    res = collection.aggregate.over_all()
    assert res.total_count == 0


def test_simple_aggregation(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(properties=[Property(name="text", data_type=DataType.TEXT)])
    collection.data.insert({"text": "some text"})
    res = collection.aggregate.over_all(return_metrics=[Metrics("text").text(count=True)])
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == 1


def test_aggregation_top_occurence_with_limit(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(properties=[Property(name="text", data_type=DataType.TEXT)])
    collection.data.insert({"text": "one"})
    collection.data.insert({"text": "one"})
    collection.data.insert({"text": "two"})
    res = collection.aggregate.over_all(
        return_metrics=[Metrics("text").text(min_occurrences=1)],
    )
    assert isinstance(res.properties["text"], AggregateText)
    assert len(res.properties["text"].top_occurrences) == 1
    assert res.properties["text"].top_occurrences[0].count == 2


def test_aggregation_groupby_with_limit(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(properties=[Property(name="text", data_type=DataType.TEXT)])
    collection.data.insert({"text": "one"})
    collection.data.insert({"text": "two"})
    collection.data.insert({"text": "three"})
    res = collection.aggregate.over_all(
        return_metrics=[Metrics("text").text(count=True)],
        group_by=GroupByAggregate(prop="text", limit=2),
    )
    assert len(res.groups) == 2
    assert res.groups[0].properties["text"].count == 1
    assert res.groups[1].properties["text"].count == 1


@pytest.mark.parametrize(
    "filter_",
    [
        Filter.by_property("text").equal("two"),
        Filter.by_property("int").equal(2),
        Filter.by_property("float").equal(2.0),
        Filter.by_property("bool").equal(False),
        Filter.by_property("date").equal(datetime(2021, 1, 2, 0, 0, 0, 0, tzinfo=timezone.utc)),
        Filter.by_property("text").equal("two") | Filter.by_property("int").equal(2),
        Filter.by_property("uuid").equal(UUID2),
        Filter.by_property("texts").contains_any(["two"]),
        Filter.by_property("ints").contains_any([2]),
        Filter.by_property("floats").contains_any([2.0]),
        Filter.by_property("bools").contains_any([False]),
        Filter.by_property("dates").contains_any(
            [datetime(2021, 1, 2, 0, 0, 0, 0, tzinfo=timezone.utc)]
        ),
        Filter.by_property("uuids").contains_any([UUID2]),
    ],
)
def test_over_all_with_filters(collection_factory: CollectionFactory, filter_: _Filters) -> None:
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="int", data_type=DataType.INT),
            Property(name="float", data_type=DataType.NUMBER),
            Property(name="bool", data_type=DataType.BOOL),
            Property(name="date", data_type=DataType.DATE),
            Property(name="uuid", data_type=DataType.UUID),
            Property(name="texts", data_type=DataType.TEXT_ARRAY),
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
            Property(name="uuids", data_type=DataType.UUID_ARRAY),
        ]
    )
    collection.data.insert(
        {
            "text": "one",
            "int": 1,
            "float": 1.0,
            "bool": True,
            "date": "2021-01-01T00:00:00Z",
            "uuid": UUID1,
            "texts": ["one"],
            "ints": [1],
            "floats": [1.0],
            "bools": [True],
            "dates": ["2021-01-01T00:00:00Z"],
            "uuids": [UUID1],
        }
    )
    collection.data.insert(
        {
            "text": "two",
            "int": 2,
            "float": 2.0,
            "bool": False,
            "date": "2021-01-02T00:00:00Z",
            "uuid": UUID2,
            "texts": ["two"],
            "ints": [2],
            "floats": [2.0],
            "bools": [False],
            "dates": ["2021-01-02T00:00:00Z"],
            "uuids": [UUID2],
        }
    )

    res = collection.aggregate.over_all(
        filters=filter_,
        return_metrics=[Metrics("text").text(count=True, top_occurrences_value=True)],
    )
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == 1
    assert res.properties["text"].top_occurrences[0].value == "two"


def test_over_all_with_filters_ref(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ]
    )
    collection.config.add_reference(
        ReferenceProperty(name="ref", target_collection=collection.name)
    )

    uuid1 = collection.data.insert({"text": "one"})
    collection.data.insert({"text": "two"}, references={"ref": uuid1})

    res = collection.aggregate.over_all(
        filters=Filter.by_ref_multi_target("ref", collection.name).by_property("text").equal("one"),
        return_metrics=[Metrics("text").text(count=True, top_occurrences_value=True)],
    )
    assert isinstance(res.properties["text"], AggregateText)
    assert res.properties["text"].count == 1
    assert res.properties["text"].top_occurrences[0].value == "two"

    with pytest.raises(WeaviateInvalidInputError):
        res = collection.aggregate.over_all(
            filters=Filter.by_ref("ref")
            .by_property("text")
            .equal("one"),  # gRPC-compat API not support by GQL aggregation
            return_metrics=[Metrics("text").text(count=True, top_occurrences_value=True)],
        )


def test_wrong_aggregation(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(properties=[Property(name="text", data_type=DataType.TEXT)])
    with pytest.raises(WeaviateQueryError) as e:
        collection.aggregate.over_all(total_count=False)
    assert (
        e.value.message
        == "The query that you sent had no body so GraphQL was unable to parse it. You must provide at least one option to the aggregation method in order to build a valid query."
    )


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
def test_near_object_aggregation(
    collection_factory: CollectionFactory, option: dict, expected_len: int
) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    res: AggregateReturn = collection.aggregate.near_object(
        uuid,
        return_metrics=[
            Metrics("text").text(count=True, top_occurrences_count=True, top_occurrences_value=True)
        ],
        **option,
    )
    assert isinstance(res.properties["text"], AggregateText)
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


def test_near_object_missing_param(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    collection.data.insert({"text": text_2})
    with pytest.raises(WeaviateInvalidInputError) as e:
        collection.aggregate.near_object(
            uuid,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


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
def test_near_vector_aggregation(
    collection_factory: CollectionFactory, option: dict, expected_len: int
) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    uuid = collection.data.insert({"text": text_1})
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert "default" in obj.vector
    collection.data.insert({"text": text_2})
    res: AggregateReturn = collection.aggregate.near_vector(
        obj.vector["default"],
        return_metrics=[
            Metrics("text").text(count=True, top_occurrences_count=True, top_occurrences_value=True)
        ],
        **option,
    )
    assert isinstance(res.properties["text"], AggregateText)
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


def test_near_vector_missing_param(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    uuid_ = collection.data.insert({"text": "some text"})
    obj = collection.query.fetch_object_by_id(uuid_, include_vector=True)
    assert "default" in obj.vector
    with pytest.raises(WeaviateInvalidInputError) as e:
        collection.aggregate.near_vector(
            obj.vector["default"],
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


@pytest.mark.parametrize(
    "option,expected_len",
    [
        ({"object_limit": 1}, 1),
        ({"certainty": 0.9}, 1),
        ({"distance": 0.1}, 1),
        ({"object_limit": 2}, 2),
        ({"certainty": 0.1}, 2),
        ({"distance": 0.9}, 2),
        ({"move_away": Move(concepts="something", force=0.000001), "distance": 0.9}, 2),
        ({"move_away": Move(objects=UUID1, force=0.000001), "distance": 0.9}, 2),
        ({"move_away": Move(concepts=["something", "else"], force=0.000001), "distance": 0.9}, 2),
        ({"move_to": Move(objects=[UUID1, UUID2], force=0.000001), "distance": 0.9}, 2),
    ],
)
def test_near_text_aggregation(
    collection_factory: CollectionFactory, option: dict, expected_len: int
) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    text_2 = "nothing like the other one at all, not even a little bit"
    collection.data.insert({"text": text_1}, uuid=UUID1)
    collection.data.insert({"text": text_2}, uuid=UUID2)
    res: AggregateReturn = collection.aggregate.near_text(
        text_1,
        return_metrics=[
            Metrics("text").text(count=True, top_occurrences_count=True, top_occurrences_value=True)
        ],
        **option,
    )
    assert isinstance(res.properties["text"], AggregateText)
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


def test_near_text_missing_param(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    text_1 = "some text"
    collection.data.insert({"text": text_1})
    with pytest.raises(WeaviateInvalidInputError) as e:
        collection.aggregate.near_text(
            text_1,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


@pytest.mark.parametrize("option", [{"object_limit": 1}, {"certainty": 0.9}, {"distance": 0.1}])
def test_near_image_aggregation(collection_factory: CollectionFactory, option: dict) -> None:
    collection = collection_factory(
        properties=[
            Property(name="rating", data_type=DataType.INT),
            Property(name="image", data_type=DataType.BLOB),
        ],
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["image"]),
    )
    img_path = pathlib.Path("integration/weaviate-logo.png")
    collection.data.insert({"image": file_encoder_b64(img_path), "rating": 9})
    res: AggregateReturn = collection.aggregate.near_image(
        img_path,
        return_metrics=[Metrics("rating").integer(count=True, maximum=True)],
        **option,
    )
    assert isinstance(res.properties["rating"], AggregateInteger)
    assert res.properties["rating"].count == 1
    assert res.properties["rating"].maximum == 9


def test_near_image_missing_param(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="rating", data_type=DataType.INT),
            Property(name="image", data_type=DataType.BLOB),
        ],
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["image"]),
    )
    img_path = pathlib.Path("integration/weaviate-logo.png")
    collection.data.insert({"image": file_encoder_b64(img_path), "rating": 9})
    with pytest.raises(WeaviateInvalidInputError) as e:
        collection.aggregate.near_image(
            img_path,
            return_metrics=[
                Metrics("text").text(
                    count=True, top_occurrences_count=True, top_occurrences_value=True
                )
            ],
        )
    assert (
        "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
        == e.value.message
    )


def test_group_by_aggregation_argument(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="int", data_type=DataType.INT),
        ],
    )
    collection.data.insert({"text": "some text", "int": 1})
    collection.data.insert({"text": "some text", "int": 2})

    res = collection.aggregate.over_all(
        group_by="text",
        return_metrics=[
            Metrics("text").text(count=True),
            Metrics("int").integer(count=True),
        ],
    )
    groups = res.groups
    assert len(groups) == 1
    assert groups[0].grouped_by.prop == "text"
    assert groups[0].grouped_by.value == "some text"
    assert isinstance(groups[0].properties["text"], AggregateText)
    assert groups[0].properties["text"].count == 2
    assert isinstance(groups[0].properties["int"], AggregateInteger)
    assert groups[0].properties["int"].count == 2

    res = collection.aggregate.over_all(
        group_by="int",
        return_metrics=[
            Metrics("text").text(count=True),
            Metrics("int").integer(count=True),
        ],
    )
    groups = res.groups
    assert len(groups) == 2
    assert groups[0].grouped_by.prop == "int"
    assert groups[0].grouped_by.value == "1" or groups[1].grouped_by.value == "1"
    assert isinstance(groups[0].properties["text"], AggregateText)
    assert groups[0].properties["text"].count == 1
    assert isinstance(groups[0].properties["int"], AggregateInteger)
    assert groups[0].properties["int"].count == 1
    assert groups[1].grouped_by.prop == "int"
    assert groups[1].grouped_by.value == "2" or groups[0].grouped_by.value == "2"
    assert isinstance(groups[1].properties["text"], AggregateText)
    assert groups[1].properties["text"].count == 1
    assert isinstance(groups[1].properties["int"], AggregateInteger)
    assert groups[1].properties["int"].count == 1


@pytest.mark.skip(reason="Validation logic is not robust enough currently")
def test_mistake_in_usage(
    collection_factory_get: CollectionFactoryGet, request: SubRequest
) -> None:
    collection = collection_factory_get(request.node.name)
    with pytest.raises(TypeError) as e:
        collection.aggregate.over_all([Metrics("text")])  # type: ignore # testing incorrect usage
    assert (
        e.value.args[0]
        == "One of the aggregations is an unexpected type: <class 'weaviate.collection.classes.aggregate.Metrics'>. Did you forget to append a method call? E.g. .text(count=True)"
    )
    with pytest.raises(TypeError) as e:
        collection.aggregate.over_all(aggregations=[Metrics("text")])  # type: ignore # testing incorrect usage
    assert (
        e.value.args[0]
        == "One of the aggregations is an unexpected type: <class 'weaviate.collection.classes.aggregate.Metrics'>. Did you forget to append a method call?  E.g. .text(count=True)"
    )


def test_all_available_aggregations(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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
        ],
    )
    collection.config.add_reference(
        ReferenceProperty(name="ref", target_collection=collection.name)
    )
    collection.data.insert(
        {
            "text": "some text",
            "texts": ["some text", "some text"],
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
            Metrics("text").text(),
            Metrics("texts").text(),
            Metrics("int").integer(),
            Metrics("ints").integer(),
            Metrics("float").number(),
            Metrics("floats").number(),
            Metrics("bool").boolean(),
            Metrics("bools").boolean(),
            Metrics("date").date_(),
            Metrics("dates").date_(),
        ]
    )

    text = res.properties["text"]
    assert isinstance(text, AggregateText)
    assert text.count == 1
    assert text.top_occurrences[0].count == 1
    assert text.top_occurrences[0].value == "some text"

    texts = res.properties["texts"]
    assert isinstance(texts, AggregateText)
    assert texts.count == 2
    assert texts.top_occurrences[0].count == 2
    assert texts.top_occurrences[0].value == "some text"

    int_ = res.properties["int"]
    assert isinstance(int_, AggregateInteger)
    assert int_.count == 1
    assert int_.maximum == 1
    assert int_.mean == 1
    assert int_.median == 1
    assert int_.minimum == 1
    assert int_.mode == 1
    assert int_.sum_ == 1

    ints = res.properties["ints"]
    assert isinstance(ints, AggregateInteger)
    assert ints.count == 2
    assert ints.maximum == 2
    assert ints.mean == 1.5
    assert ints.median == 1.5
    assert ints.minimum == 1
    assert ints.mode == 1

    float_ = res.properties["float"]
    assert isinstance(float_, AggregateNumber)
    assert float_.count == 1
    assert float_.maximum == 1.0
    assert float_.mean == 1.0
    assert float_.median == 1.0
    assert float_.minimum == 1.0
    assert float_.mode == 1.0

    floats = res.properties["floats"]
    assert isinstance(floats, AggregateNumber)
    assert floats.count == 2
    assert floats.maximum == 2.0
    assert floats.mean == 1.5
    assert floats.median == 1.5
    assert floats.minimum == 1.0
    assert floats.mode == 1.0

    bool_ = res.properties["bool"]
    assert isinstance(bool_, AggregateBoolean)
    assert bool_.count == 1
    assert bool_.percentage_false == 0
    assert bool_.percentage_true == 1
    assert bool_.total_false == 0
    assert bool_.total_true == 1

    bools = res.properties["bools"]
    assert isinstance(bools, AggregateBoolean)
    assert bools.count == 2
    assert bools.percentage_false == 0.5
    assert bools.percentage_true == 0.5
    assert bools.total_false == 1
    assert bools.total_true == 1

    date = res.properties["date"]
    assert isinstance(date, AggregateDate)
    assert date.count == 1
    assert date.maximum == "2021-01-01T00:00:00Z"
    assert date.median == "2021-01-01T00:00:00Z"
    assert date.minimum == "2021-01-01T00:00:00Z"
    assert date.mode == "2021-01-01T00:00:00Z"

    dates = res.properties["dates"]
    assert isinstance(dates, AggregateDate)
    assert dates.count == 2
    assert dates.maximum == "2021-01-02T00:00:00Z"
    assert dates.median == "2021-01-01T12:00:00Z"
    assert dates.minimum == "2021-01-01T00:00:00Z"
    # assert res.properties["dates"].mode == "2021-01-02T00:00:00Z" # flakey: sometimes return 01, other times 02

import datetime
import uuid
from typing import List

import pytest as pytest

import weaviate
from weaviate.collections.classes.config import (
    Configure,
    Property,
    DataType,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    Tokenization,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.filters import (
    Filter,
    _Filters,
    _FilterValue,
)
from weaviate.collections.classes.grpc import MetadataQuery
from weaviate.collections.classes.internal import Reference

NOW = datetime.datetime.now(datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
MUCH_LATER = NOW + datetime.timedelta(days=1)

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()


@pytest.fixture(scope="module")
def client():
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter(path="name").equal("Banana"), [0]),
        (Filter(path="name").not_equal("Banana"), [1, 2]),
        (Filter(path="name").like("*nana"), [0]),
    ],
)
def test_filters_text(
    client: weaviate.WeaviateClient, weaviate_filter: _FilterValue, results: List[int]
):
    client.collections.delete("TestFilterText")
    collection = client.collections.create(
        name="TestFilterText",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    uuids = [
        collection.data.insert({"name": "Banana"}),
        collection.data.insert({"name": "Apple"}),
        collection.data.insert({"name": "Mountain"}),
    ]

    objects = collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.metadata.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter(path="num").greater_than(1) & Filter(path="num").less_than(3), [1]),
        (
            (Filter(path="num").less_or_equal(1)) | Filter(path="num").greater_or_equal(3),
            [0, 2],
        ),
        (
            Filter(path="num").less_or_equal(1) | Filter(path="num").greater_or_equal(3),
            [0, 2],
        ),
        (
            (Filter(path="num").less_or_equal(1) & Filter(path="num").greater_or_equal(1))
            | Filter(path="num").greater_or_equal(3)
            | Filter(path="num").is_none(True),
            [0, 2, 3],
        ),
    ],
)
def test_filters_nested(
    client: weaviate.WeaviateClient,
    weaviate_filter: _Filters,
    results: List[int],
):
    client.collections.delete("TestFilterNested")
    collection = client.collections.create(
        name="TestFilterNested",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="num", data_type=DataType.NUMBER)],
        inverted_index_config=Configure.inverted_index(index_null_state=True),
    )

    uuids = [
        collection.data.insert({"num": 1.0}),
        collection.data.insert({"num": 2.0}),
        collection.data.insert({"num": 3.0}),
        collection.data.insert({"num": None}),
    ]

    objects = collection.query.fetch_objects(
        filters=weaviate_filter, return_metadata=MetadataQuery(uuid=True)
    ).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.metadata.uuid in uuids for obj in objects)


def test_length_filter(client: weaviate.WeaviateClient):
    client.collections.delete("TestFilterNested")
    collection = client.collections.create(
        name="TestFilterNested",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="field", data_type=DataType.TEXT)],
        inverted_index_config=Configure.inverted_index(index_property_length=True),
    )
    uuids = [
        collection.data.insert({"field": "one"}),
        collection.data.insert({"field": "two"}),
        collection.data.insert({"field": "three"}),
        collection.data.insert({"field": "four"}),
    ]
    objects = collection.query.fetch_objects(
        filters=Filter(path="field", length=True).equal(3)
    ).objects

    results = [0, 1]
    assert len(objects) == len(results)
    uuids = [uuids[result] for result in results]
    assert all(obj.metadata.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter(path="number").is_none(True), [3]),
        (Filter(path="number").is_none(False), [0, 1, 2]),
    ],
)
def test_filters_comparison(
    client: weaviate.WeaviateClient, weaviate_filter: _FilterValue, results: List[int]
):
    client.collections.delete("TestFilterNumber")
    collection = client.collections.create(
        name="TestFilterNumber",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="number", data_type=DataType.INT)],
        inverted_index_config=Configure.inverted_index(index_null_state=True),
    )

    uuids = [
        collection.data.insert({"number": 1}),
        collection.data.insert({"number": 2}),
        collection.data.insert({"number": 3}),
        collection.data.insert({"number": None}),
    ]

    objects = collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.metadata.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter(path="nums").contains_any([1, 4]), [0, 3]),
        (Filter(path="nums").contains_any([10]), []),
        (Filter(path="num").contains_any([1]), [0, 1]),
        (Filter(path="text").contains_any(["test"]), [0, 1]),
        (Filter(path="text").contains_any(["real", "deal"]), [1, 2, 3]),
        (Filter(path="texts").contains_any(["test"]), [0, 1]),
        (Filter(path="texts").contains_any(["real", "deal"]), [1, 2, 3]),
        (Filter(path="float").contains_any([2.0]), []),
        (Filter(path="float").contains_any([2]), []),
        (Filter(path="float").contains_any([8]), [3]),
        (Filter(path="float").contains_any([8.0]), [3]),
        (Filter(path="floats").contains_any([2.0]), [0, 1]),
        (Filter(path="floats").contains_any([0.4, 0.7]), [0, 1, 3]),
        (Filter(path="floats").contains_any([2]), [0, 1]),
        (Filter(path="bools").contains_any([True, False]), [0, 1, 3]),
        (Filter(path="bools").contains_any([False]), [0, 1]),
        (Filter(path="bool").contains_any([True]), [0, 1, 3]),
        (Filter(path="nums").contains_all([1, 4]), [0]),
        (Filter(path="text").contains_all(["real", "test"]), [1]),
        (Filter(path="texts").contains_all(["real", "test"]), [1]),
        (Filter(path="floats").contains_all([0.7, 2]), [1]),
        (Filter(path="bools").contains_all([True, False]), [0]),
        (Filter(path="bool").contains_all([True, False]), []),
        (Filter(path="bool").contains_all([True]), [0, 1, 3]),
        (Filter(path="dates").contains_any([NOW, MUCH_LATER]), [0, 1, 3]),
        (Filter(path="dates").contains_any([NOW]), [0, 1]),
        (Filter(path="date").equal(NOW), [0]),
        (Filter(path="date").greater_than(NOW), [1, 3]),
        (Filter(path="uuids").contains_all([UUID2, UUID1]), [0, 3]),
        (Filter(path="uuids").contains_any([UUID2, UUID1]), [0, 1, 3]),
        (Filter(path="uuid").contains_any([UUID3]), []),
        (Filter(path="uuid").contains_any([UUID1]), [0]),
    ],
)
def test_filters_contains(
    client: weaviate.WeaviateClient, weaviate_filter: _FilterValue, results: List[int]
):
    client.collections.delete("TestFilterContains")
    collection = client.collections.create(
        name="TestFilterContains",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="texts", data_type=DataType.TEXT_ARRAY),
            Property(name="num", data_type=DataType.INT),
            Property(name="nums", data_type=DataType.INT_ARRAY),
            Property(name="float", data_type=DataType.NUMBER),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="bool", data_type=DataType.BOOL),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
            Property(name="date", data_type=DataType.DATE),
            Property(name="uuids", data_type=DataType.UUID_ARRAY),
            Property(name="uuid", data_type=DataType.UUID),
        ],
    )

    uuids = [
        collection.data.insert(
            {
                "text": "this is a test",
                "texts": "this is a test".split(" "),
                "num": 1,
                "nums": [1, 2, 4],
                "float": 0.5,
                "floats": [0.4, 0.9, 2],
                "bool": True,
                "bools": [True, False],
                "dates": [NOW, LATER, MUCH_LATER],
                "date": NOW,
                "uuids": [UUID1, UUID3, UUID2],
                "uuid": UUID1,
            }
        ),
        collection.data.insert(
            {
                "text": "this is not a real test",
                "texts": "this is not a real test".split(" "),
                "num": 1,
                "nums": [5, 6, 9],
                "float": 0.3,
                "floats": [0.1, 0.7, 2],
                "bool": True,
                "bools": [False, False],
                "dates": [NOW, NOW, MUCH_LATER],
                "date": LATER,
                "uuids": [UUID2, UUID2],
                "uuid": UUID2,
            }
        ),
        collection.data.insert(
            {
                "text": "real deal",
                "texts": "real deal".split(" "),
                "num": 3,
                "nums": [],
                "floats": [],
                "bool": False,
                "bools": [],
                "dates": [],
                "uuids": [],
            }
        ),
        collection.data.insert(
            {
                "text": "not real deal",
                "texts": "not real deal".split(" "),
                "num": 4,
                "nums": [4],
                "float": 8,
                "floats": [0.7],
                "bool": True,
                "bools": [True],
                "dates": [MUCH_LATER],
                "date": MUCH_LATER,
                "uuids": [UUID1, UUID2],
                "uuid": UUID2,
            }
        ),
    ]

    objects = collection.query.fetch_objects(
        filters=weaviate_filter, return_metadata=MetadataQuery(uuid=True)
    ).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.metadata.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter(path=["ref", "TestFilterRef2", "int"]).greater_than(3), [1]),
        (Filter(path=["ref", "TestFilterRef2", "text"], length=True).less_than(6), [0]),
    ],
)
def test_ref_filters(
    client: weaviate.WeaviateClient, weaviate_filter: _FilterValue, results: List[int]
):
    client.collections.delete("TestFilterRef")
    client.collections.delete("TestFilterRef2")
    to_collection = client.collections.create(
        name="TestFilterRef2",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int", data_type=DataType.INT),
            Property(name="text", data_type=DataType.TEXT),
        ],
        inverted_index_config=Configure.inverted_index(index_property_length=True),
    )
    uuids_to = [
        to_collection.data.insert(properties={"int": 0, "text": "first"}),
        to_collection.data.insert(properties={"int": 15, "text": "second"}),
    ]
    from_collection = client.collections.create(
        name="TestFilterRef",
        properties=[
            ReferenceProperty(name="ref", target_collection="TestFilterRef2"),
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuids_from = [
        from_collection.data.insert({"ref": Reference.to(uuids_to[0]), "name": "first"}),
        from_collection.data.insert({"ref": Reference.to(uuids_to[1]), "name": "second"}),
    ]

    objects = from_collection.query.fetch_objects(
        filters=weaviate_filter, return_metadata=MetadataQuery(uuid=True)
    ).objects
    assert len(objects) == len(results)

    uuids = [uuids_from[result] for result in results]
    assert all(obj.metadata.uuid in uuids for obj in objects)


def test_ref_filters_multi_target(client: weaviate.WeaviateClient):
    target = "TestFilterRefMulti2"
    source = "TestFilterRefMulti"
    client.collections.delete(source)
    client.collections.delete(target)
    to_collection = client.collections.create(
        name=target,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="int", data_type=DataType.INT)],
    )
    uuid_to = to_collection.data.insert(properties={"int": 0})
    uuid_to2 = to_collection.data.insert(properties={"int": 5})
    from_collection = client.collections.create(
        name=source,
        properties=[
            ReferencePropertyMultiTarget(
                name="ref", target_collections=[target, "TestFilterRefMulti"]
            ),
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid_from_to_target1 = from_collection.data.insert(
        {
            "ref": Reference.to_multi_target(uuids=uuid_to, target_collection=target),
            "name": "first",
        }
    )
    uuid_from_to_target2 = from_collection.data.insert(
        {
            "ref": Reference.to_multi_target(uuids=uuid_to2, target_collection=target),
            "name": "second",
        }
    )
    from_collection.data.insert(
        {
            "ref": Reference.to_multi_target(uuids=uuid_from_to_target1, target_collection=source),
            "name": "third",
        }
    )
    from_collection.data.insert(
        {
            "ref": Reference.to_multi_target(uuids=uuid_from_to_target2, target_collection=source),
            "name": "fourth",
        }
    )

    objects = from_collection.query.fetch_objects(
        filters=Filter(path=["ref", target, "int"]).greater_than(3)
    ).objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "second"

    objects = from_collection.query.fetch_objects(
        filters=Filter(path=["ref", source, "name"]).equal("first")
    ).objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "third"


@pytest.mark.parametrize(
    "properties,objects,where,expected_len",
    [
        (
            [
                Property(name="text", data_type=DataType.TEXT),
            ],
            [
                DataObject(properties={"text": "text"}, uuid=uuid.uuid4()),
            ],
            Filter("text").equal("text"),
            0,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
            ],
            [
                DataObject(properties={"text": "there is some text in here"}, uuid=uuid.uuid4()),
            ],
            Filter("text").like("text"),
            0,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
            ],
            [
                DataObject(properties={"text": "banana"}, uuid=uuid.uuid4()),
            ],
            Filter("text").like("ba*"),
            0,
        ),
        (
            [
                Property(name="texts", data_type=DataType.TEXT_ARRAY),
            ],
            [
                DataObject(properties={"texts": ["text1", "text2"]}, uuid=uuid.uuid4()),
            ],
            Filter("texts").contains_all(["text1", "text2"]),
            0,
        ),
        (
            [
                Property(name="texts", data_type=DataType.TEXT_ARRAY),
            ],
            [
                DataObject(properties={"texts": ["text1"]}, uuid=uuid.uuid4()),
                DataObject(properties={"texts": ["text2"]}, uuid=uuid.uuid4()),
            ],
            Filter("texts").contains_any(["text1"]),
            1,
        ),
        (
            [Property(name="int", data_type=DataType.INT)],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
            ],
            Filter("int").equal(10),
            0,
        ),
        (
            [
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
            ],
            Filter("int").greater_than(5),
            0,
        ),
        (
            [
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
            ],
            Filter("int").less_than(15),
            0,
        ),
        (
            [
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
                DataObject(properties={"int": 15}, uuid=uuid.uuid4()),
            ],
            Filter("int").greater_or_equal(10),
            0,
        ),
        (
            [
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
                DataObject(properties={"int": 5}, uuid=uuid.uuid4()),
            ],
            Filter("int").less_or_equal(10),
            0,
        ),
        (
            [
                Property(name="ints", data_type=DataType.INT_ARRAY),
            ],
            [
                DataObject(properties={"ints": [1, 2]}, uuid=uuid.uuid4()),
            ],
            Filter("ints").contains_all([1, 2]),
            0,
        ),
        (
            [
                Property(name="ints", data_type=DataType.INT_ARRAY),
            ],
            [
                DataObject(properties={"ints": [1]}, uuid=uuid.uuid4()),
                DataObject(properties={"ints": [2]}, uuid=uuid.uuid4()),
            ],
            Filter("ints").contains_any([1]),
            1,
        ),
        (
            [
                Property(name="float", data_type=DataType.NUMBER),
            ],
            [
                DataObject(properties={"float": 1.0}, uuid=uuid.uuid4()),
            ],
            Filter("float").equal(1.0),
            0,
        ),
        (
            [
                Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            ],
            [
                DataObject(properties={"floats": [1.0, 2.0]}, uuid=uuid.uuid4()),
            ],
            Filter("floats").contains_all([1.0, 2.0]),
            0,
        ),
        (
            [
                Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            ],
            [
                DataObject(properties={"floats": [1.0]}, uuid=uuid.uuid4()),
                DataObject(properties={"floats": [2.0]}, uuid=uuid.uuid4()),
            ],
            Filter("floats").contains_any([1.0]),
            1,
        ),
        (
            [
                Property(name="float", data_type=DataType.NUMBER),
            ],
            [
                DataObject(properties={"float": 10.0}, uuid=uuid.uuid4()),
                DataObject(properties={"float": 5.0}, uuid=uuid.uuid4()),
            ],
            Filter("float").greater_than(
                5.0
            ),  # issue here, doing .greater_than(5) interprets valueInt instead of valueNumber and fails the request
            1,
        ),
        (
            [
                Property(name="bool", data_type=DataType.BOOL),
            ],
            [
                DataObject(properties={"bool": True}, uuid=uuid.uuid4()),
                DataObject(properties={"bool": False}, uuid=uuid.uuid4()),
            ],
            Filter("bool").equal(True),
            1,
        ),
        (
            [
                Property(name="bools", data_type=DataType.BOOL_ARRAY),
            ],
            [
                DataObject(properties={"bools": [True, False]}, uuid=uuid.uuid4()),
            ],
            Filter("bools").contains_all([True, False]),
            0,
        ),
        (
            [
                Property(name="bools", data_type=DataType.BOOL_ARRAY),
            ],
            [
                DataObject(properties={"bools": [True]}, uuid=uuid.uuid4()),
                DataObject(properties={"bools": [False]}, uuid=uuid.uuid4()),
            ],
            Filter("bools").contains_any([True]),
            1,
        ),
        (
            [
                Property(name="date", data_type=DataType.DATE),
            ],
            [
                DataObject(properties={"date": NOW}, uuid=uuid.uuid4()),
            ],
            Filter("date").equal(NOW),
            0,
        ),
        (
            [
                Property(name="dates", data_type=DataType.DATE_ARRAY),
            ],
            [
                DataObject(properties={"dates": [NOW, LATER]}, uuid=uuid.uuid4()),
            ],
            Filter("dates").contains_all([NOW, LATER]),
            0,
        ),
        (
            [
                Property(name="dates", data_type=DataType.DATE_ARRAY),
            ],
            [
                DataObject(properties={"dates": [NOW]}, uuid=uuid.uuid4()),
                DataObject(properties={"dates": [LATER]}, uuid=uuid.uuid4()),
            ],
            Filter("dates").contains_any([NOW]),
            1,
        ),
        (
            [
                Property(name="uuid", data_type=DataType.UUID),
            ],
            [
                DataObject(properties={"uuid": UUID1}, uuid=uuid.uuid4()),
            ],
            Filter("uuid").equal(UUID1),
            0,
        ),
        (
            [
                Property(name="uuids", data_type=DataType.UUID_ARRAY),
            ],
            [
                DataObject(properties={"uuids": [UUID1, UUID2]}, uuid=uuid.uuid4()),
            ],
            Filter("uuids").contains_all([UUID1, UUID2]),
            0,
        ),
        (
            [
                Property(name="uuids", data_type=DataType.UUID_ARRAY),
            ],
            [
                DataObject(properties={"uuids": [UUID1]}, uuid=uuid.uuid4()),
                DataObject(properties={"uuids": [UUID2]}, uuid=uuid.uuid4()),
            ],
            Filter("uuids").contains_any([UUID1]),
            1,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT, tokenization=Tokenization.FIELD),
            ],
            [
                DataObject(properties={"text": "some name"}, vector=[1, 2, 3]),
                DataObject(properties={"text": "some other name"}, uuid=uuid.uuid4()),
            ],
            Filter("text").equal("some name"),
            1,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT, tokenization=Tokenization.FIELD),
            ],
            [
                DataObject(properties={"text": "some name"}, vector=[1, 2, 3]),
                DataObject(properties={"text": "some other name"}, uuid=uuid.uuid4()),
            ],
            Filter("text").equal("some other name"),
            1,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"text": "Loads of money", "int": 60}, uuid=uuid.uuid4()),
                DataObject(properties={"text": "Lots of money", "int": 40}, uuid=uuid.uuid4()),
            ],
            Filter("text").equal("money"),
            0,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
                DataObject(properties={"text": "I am ageless"}, uuid=uuid.uuid4()),
            ],
            Filter("int").is_none(True),
            1,
        ),
    ],
)
def test_delete_many_simple(
    client: weaviate.WeaviateClient,
    properties: List[Property],
    objects: List[DataObject],
    where: _FilterValue,
    expected_len: int,
):
    name = "TestDeleteManySimple"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=properties,
        inverted_index_config=Configure.inverted_index(index_null_state=True),
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many(objects)
    assert len(collection.query.fetch_objects().objects) == len(objects)

    collection.data.delete_many(where=where)
    objects = collection.query.fetch_objects().objects
    assert len(objects) == expected_len


def test_delete_many_and(client: weaviate.WeaviateClient):
    name = "TestDeleteManyAnd"
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many(
        [
            DataObject(properties={"age": 10, "name": "Timmy"}, uuid=uuid.uuid4()),
            DataObject(properties={"age": 10, "name": "Tommy"}, uuid=uuid.uuid4()),
        ]
    )
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 2

    collection.data.delete_many(
        where=Filter(path="age").equal(10) & Filter(path="name").equal("Timmy")
    )

    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["age"] == 10
    assert objects[0].properties["name"] == "Tommy"


def test_delete_many_or(client: weaviate.WeaviateClient):
    name = "TestDeleteManyOr"
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many(
        [
            DataObject(properties={"age": 10, "name": "Timmy"}, uuid=uuid.uuid4()),
            DataObject(properties={"age": 20, "name": "Tim"}, uuid=uuid.uuid4()),
            DataObject(properties={"age": 30, "name": "Timothy"}, uuid=uuid.uuid4()),
        ]
    )
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 3

    collection.data.delete_many(where=Filter(path="age").equal(10) | Filter(path="age").equal(30))
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["age"] == 20
    assert objects[0].properties["name"] == "Tim"


def test_delete_many_return(client: weaviate.WeaviateClient):
    name = "TestDeleteManyReturn"
    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many(
        [
            DataObject(properties={"name": "delet me"}, uuid=uuid.uuid4()),
        ]
    )
    ret = collection.data.delete_many(where=Filter(path="name").equal("delet me"))
    assert ret.failed == 0
    assert ret.matches == 1
    assert ret.objects is None
    assert ret.successful == 1

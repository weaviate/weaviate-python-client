import datetime
import uuid
from typing import List, Optional, Union

import pytest as pytest

import weaviate
from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    Property,
    DataType,
    ReferenceProperty,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.filters import (
    _FilterCreationTime,
    _FilterUpdateTime,
    _FilterValue2,
    Filter,
    _Filters,
    _FilterValue,
)
from weaviate.collections.classes.grpc import MetadataQuery
from weaviate.collections.classes.internal import Reference
from weaviate.util import _ServerVersion

NOW = datetime.datetime.now(datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
MUCH_LATER = NOW + datetime.timedelta(days=1)

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter.by_property("name").equal("Banana"), [0]),
        (Filter.by_property("name").not_equal("Banana"), [1, 2]),
        (Filter.by_property("name").like("*nana"), [0]),
    ],
)
def test_filters_text(
    collection_factory: CollectionFactory,
    weaviate_filter: _Filters,
    results: List[int],
) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    if isinstance(
        weaviate_filter, _FilterValue2
    ) and collection._connection._weaviate_version < _ServerVersion(1, 23, patch=2):
        pytest.skip("new filters are not supported in this version")

    uuids = [
        collection.data.insert({"name": "Banana"}),
        collection.data.insert({"name": "Apple"}),
        collection.data.insert({"name": "Mountain"}),
    ]

    objects = collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter.by_property("texts").like("*nana"), [1]),
        (Filter.by_property("texts").equal("banana"), [1]),
        (Filter.by_property("ints").equal(3), [1]),
        (Filter.by_property("ints").greater_or_equal(3), [1, 2]),
        (Filter.by_property("floats").equal(3), [1]),
        (Filter.by_property("floats").less_or_equal(3), [0, 1]),
    ],
)
def test_array_types(
    collection_factory: CollectionFactory,
    weaviate_filter: _FilterValue,
    results: List[int],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="texts", data_type=DataType.TEXT_ARRAY),
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
        ],
    )

    if not collection._connection._weaviate_version.is_at_least(1, 23, 0):
        pytest.skip("Fixes for this are not implemented in this version")

    uuids = [
        collection.data.insert({"texts": ["an", "apple"], "ints": [1, 2], "floats": [1.0, 2.0]}),
        collection.data.insert({"texts": ["a", "banana"], "ints": [2, 3], "floats": [2.0, 3.0]}),
        collection.data.insert({"texts": ["a", "text"], "ints": [4, 5], "floats": [4.0, 5.0]}),
    ]

    objects = collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter.by_property("int").equal(1), [0]),
        (Filter.by_property("int").equal(val=1.0), [0]),
        (Filter.by_property("int").equal(val=1.2), None),
        (Filter.by_property("float").equal(val=1), [0]),
        (Filter.by_property("float").equal(val=1.0), [0]),
    ],
)
def test_filter_with_wrong_types(
    collection_factory: CollectionFactory,
    weaviate_filter: _FilterValue,
    results: Optional[List[int]],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int", data_type=DataType.INT),
            Property(name="float", data_type=DataType.NUMBER),
        ],
    )
    if not collection._connection._weaviate_version.is_at_least(1, 23, 0):
        pytest.skip("Fixes for this are not implemented in this version")

    uuids = [
        collection.data.insert({"int": 1, "float": 1.0}),
        collection.data.insert({"int": 2, "float": 2.0}),
        collection.data.insert({"int": 3, "float": 3.0}),
    ]

    if results is not None:
        objects = collection.query.fetch_objects(filters=weaviate_filter).objects
        assert len(objects) == len(results)

        uuids = [uuids[result] for result in results]
        assert all(obj.uuid in uuids for obj in objects)
    else:
        with pytest.raises(weaviate.exceptions.WeaviateGRPCQueryError):
            collection.query.fetch_objects(filters=weaviate_filter).objects


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter.by_property("num").greater_than(1) & Filter.by_property("num").less_than(3), [1]),
        (
            (Filter.by_property("num").less_or_equal(1))
            | Filter.by_property("num").greater_or_equal(3),
            [0, 2],
        ),
        (
            Filter.by_property("num").less_or_equal(1)
            | Filter.by_property("num").greater_or_equal(3),
            [0, 2],
        ),
        (
            (
                Filter.by_property("num").less_or_equal(1)
                & Filter.by_property("num").greater_or_equal(1)
            )
            | Filter.by_property("num").greater_or_equal(3)
            | Filter.by_property("num").is_none(True),
            [0, 2, 3],
        ),
    ],
)
def test_filters_nested(
    collection_factory: CollectionFactory,
    weaviate_filter: _Filters,
    results: List[int],
) -> None:
    collection = collection_factory(
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

    objects = collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.uuid in uuids for obj in objects)


def test_length_filter(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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
        filters=Filter.by_property(prop="field", length=True).equal(3)
    ).objects

    results = [0, 1]
    assert len(objects) == len(results)
    uuids = [uuids[result] for result in results]
    assert all(obj.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter.by_property("number").is_none(True), [3]),
        (Filter.by_property("number").is_none(False), [0, 1, 2]),
    ],
)
def test_filters_comparison(
    collection_factory: CollectionFactory,
    weaviate_filter: _FilterValue,
    results: List[int],
) -> None:
    collection = collection_factory(
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
    assert all(obj.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results,skip",
    [
        (Filter.by_property("ints").contains_any([1, 4]), [0, 3], False),
        (Filter.by_property("ints").contains_any([1.0, 4]), [0, 3], True),
        (Filter.by_property("ints").contains_any([10]), [], False),
        (Filter.by_property("int").contains_any([1]), [0, 1], False),
        (Filter.by_property("text").contains_any(["test"]), [0, 1], False),
        (Filter.by_property("text").contains_any(["real", "deal"]), [1, 2, 3], False),
        (Filter.by_property("texts").contains_any(["test"]), [0, 1], False),
        (Filter.by_property("texts").contains_any(["real", "deal"]), [1, 2, 3], False),
        (Filter.by_property("float").contains_any([2.0]), [], False),
        (Filter.by_property("float").contains_any([2]), [], False),
        (Filter.by_property("float").contains_any([8]), [3], False),
        (Filter.by_property("float").contains_any([8.0]), [3], False),
        (Filter.by_property("floats").contains_any([2.0]), [0, 1], False),
        (Filter.by_property("floats").contains_any([0.4, 0.7]), [0, 1, 3], False),
        (Filter.by_property("floats").contains_any([2]), [0, 1], False),
        (Filter.by_property("bools").contains_any([True, False]), [0, 1, 3], False),
        (Filter.by_property("bools").contains_any([False]), [0, 1], False),
        (Filter.by_property("bool").contains_any([True]), [0, 1, 3], False),
        (Filter.by_property("ints").contains_all([1, 4]), [0], False),
        (Filter.by_property("text").contains_all(["real", "test"]), [1], False),
        (Filter.by_property("texts").contains_all(["real", "test"]), [1], False),
        (Filter.by_property("floats").contains_all([0.7, 2]), [1], False),
        (Filter.by_property("bools").contains_all([True, False]), [0], False),
        (Filter.by_property("bool").contains_all([True, False]), [], False),
        (Filter.by_property("bool").contains_all([True]), [0, 1, 3], False),
        (Filter.by_property("dates").contains_any([NOW, MUCH_LATER]), [0, 1, 3], False),
        (Filter.by_property("dates").contains_any([NOW]), [0, 1], False),
        (Filter.by_property("date").equal(NOW), [0], False),
        (Filter.by_property("date").greater_than(NOW), [1, 3], False),
        (Filter.by_property("uuids").contains_all([UUID2, UUID1]), [0, 3], False),
        (Filter.by_property("uuids").contains_any([UUID2, UUID1]), [0, 1, 3], False),
        (Filter.by_property("uuid").contains_any([UUID3]), [], False),
        (Filter.by_property("uuid").contains_any([UUID1]), [0], False),
        (Filter.by_property("_id").contains_any([UUID1, UUID3]), [0, 2], True),
    ],
)
def test_filters_contains(
    collection_factory: CollectionFactory,
    weaviate_filter: _FilterValue,
    results: List[int],
    skip: bool,
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="texts", data_type=DataType.TEXT_ARRAY),
            Property(name="int", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
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
    if not collection._connection._weaviate_version.is_at_least(1, 23, 0) and skip:
        pytest.skip("not supported in this version")

    uuids = [
        collection.data.insert(
            {
                "text": "this is a test",
                "texts": "this is a test".split(" "),
                "int": 1,
                "ints": [1, 2, 4],
                "float": 0.5,
                "floats": [0.4, 0.9, 2],
                "bool": True,
                "bools": [True, False],
                "dates": [NOW, LATER, MUCH_LATER],
                "date": NOW,
                "uuids": [UUID1, UUID3, UUID2],
                "uuid": UUID1,
            },
            uuid=UUID1,
        ),
        collection.data.insert(
            {
                "text": "this is not a real test",
                "texts": "this is not a real test".split(" "),
                "int": 1,
                "ints": [5, 6, 9],
                "float": 0.3,
                "floats": [0.1, 0.7, 2],
                "bool": True,
                "bools": [False, False],
                "dates": [NOW, NOW, MUCH_LATER],
                "date": LATER,
                "uuids": [UUID2, UUID2],
                "uuid": UUID2,
            },
            uuid=UUID2,
        ),
        collection.data.insert(
            {
                "text": "real deal",
                "texts": "real deal".split(" "),
                "int": 3,
                "ints": [],
                "floats": [],
                "bool": False,
                "bools": [],
                "dates": [],
                "uuids": [],
            },
            uuid=UUID3,
        ),
        collection.data.insert(
            {
                "text": "not real deal",
                "texts": "not real deal".split(" "),
                "int": 4,
                "ints": [4],
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

    objects = collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids[result] for result in results]
    assert all(obj.uuid in uuids for obj in objects)


@pytest.mark.parametrize(
    "weaviate_filter,results",
    [
        (Filter.by_ref().link_on("ref").by_property("int").greater_than(3), [1]),
        (Filter.by_ref().link_on("ref").by_property("text", length=True).less_than(6), [0]),
        (Filter.by_ref().link_on("ref").by_id().equal(UUID2), [1]),
        (
            Filter.by_ref()
            .link_on("ref2")
            .link_on("ref")
            .by_property("text", length=True)
            .less_than(6),
            [2],
        ),  # second obj links to first one
    ],
)
def test_ref_filters(
    collection_factory: CollectionFactory, weaviate_filter: _Filters, results: List[int]
) -> None:
    to_collection = collection_factory(
        name="Target",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int", data_type=DataType.INT),
            Property(name="text", data_type=DataType.TEXT),
        ],
        inverted_index_config=Configure.inverted_index(index_property_length=True),
    )
    if isinstance(weaviate_filter, _FilterValue):
        assert isinstance(weaviate_filter.path, list)

        # enable filters with direct path
        if len(weaviate_filter.path) > 1:
            weaviate_filter.path[1] = to_collection.name

        if (
            to_collection._connection._weaviate_version < _ServerVersion(1, 23, patch=0)
            and "_id" in weaviate_filter.path
        ):
            pytest.skip("filter by id is not supported in this version")

    # patch=3 in reality, but to be able to test this
    if to_collection._connection._weaviate_version < _ServerVersion(1, 23, patch=2) and isinstance(
        weaviate_filter, _FilterValue2
    ):
        pytest.skip("new filters are not supported in this version")

    uuids_to = [
        to_collection.data.insert(properties={"int": 0, "text": "first"}, uuid=UUID1),
        to_collection.data.insert(properties={"int": 15, "text": "second"}, uuid=UUID2),
    ]
    from_collection = collection_factory(
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        references=[ReferenceProperty(name="ref", target_collection=to_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    from_collection.config.add_reference(
        ReferenceProperty(name="ref2", target_collection=from_collection.name)
    )

    uuids_from = [
        from_collection.data.insert(
            properties={"name": "first"}, references={"ref": Reference.to(uuids_to[0])}
        ),
        from_collection.data.insert(
            properties={"name": "second"}, references={"ref": Reference.to(uuids_to[1])}
        ),
    ]
    uuids_from.extend(
        [
            from_collection.data.insert(
                properties={"name": "third"}, references={"ref2": Reference.to(uuids_from[0])}
            ),
            from_collection.data.insert(
                properties={"name": "fourth"}, references={"ref2": Reference.to(uuids_from[1])}
            ),
        ]
    )

    objects = from_collection.query.fetch_objects(filters=weaviate_filter).objects
    assert len(objects) == len(results)

    uuids = [uuids_from[result] for result in results]
    assert all(obj.uuid in uuids for obj in objects)


def test_ref_filters_multi_target(collection_factory: CollectionFactory) -> None:
    to_collection = collection_factory(
        name="target",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="int", data_type=DataType.INT)],
    )
    uuid_to = to_collection.data.insert(properties={"int": 0})
    uuid_to2 = to_collection.data.insert(properties={"int": 5})
    from_collection = collection_factory(
        name="source",
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    from_collection.config.add_reference(
        ReferenceProperty.MultiTarget(
            name="ref", target_collections=[to_collection.name, from_collection.name]
        )
    )

    uuid_from_to_target1 = from_collection.data.insert(
        {
            "name": "first",
        },
        references={
            "ref": Reference.to_multi_target(uuids=uuid_to, target_collection=to_collection.name),
        },
    )
    uuid_from_to_target2 = from_collection.data.insert(
        {
            "name": "second",
        },
        references={
            "ref": Reference.to_multi_target(uuids=uuid_to2, target_collection=to_collection.name),
        },
    )
    from_collection.data.insert(
        {
            "name": "third",
        },
        references={
            "ref": Reference.to_multi_target(
                uuids=uuid_from_to_target1, target_collection=from_collection.name
            ),
        },
    )
    from_collection.data.insert(
        {
            "name": "fourth",
        },
        references={
            "ref": Reference.to_multi_target(
                uuids=uuid_from_to_target2, target_collection=from_collection.name
            ),
        },
    )

    objects = from_collection.query.fetch_objects(
        filters=Filter.by_ref()
        .link_on_multi("ref", to_collection.name)
        .by_property("int")
        .greater_than(3)
    ).objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "second"

    objects = from_collection.query.fetch_objects(
        filters=Filter.by_ref()
        .link_on_multi("ref", target_collection=from_collection.name)
        .by_property("name")
        .equal("first")
    ).objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "third"


@pytest.mark.parametrize(
    "weav_filter",
    [
        Filter.by_id().equal(UUID1),
        Filter.by_id().contains_any([UUID1]),
        Filter.by_id().not_equal(UUID2),
        Filter.by_property("_id").equal(UUID1),
    ],
)
def test_filter_id(collection_factory: CollectionFactory, weav_filter: _FilterValue) -> None:
    collection = collection_factory(
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    if not collection._connection._weaviate_version.is_at_least(1, 23, 0):
        pytest.skip("filter by id is not supported in this version")

    collection.data.insert_many(
        [
            DataObject(properties={"name": "first"}, uuid=UUID1),
            DataObject(properties={"name": "second"}, uuid=UUID2),
        ]
    )

    objects = collection.query.fetch_objects(filters=weav_filter).objects

    assert len(objects) == 1
    assert objects[0].uuid == UUID1


@pytest.mark.parametrize("path", ["_creationTimeUnix", "_lastUpdateTimeUnix"])
def test_filter_timestamp_direct_path(collection_factory: CollectionFactory, path: str) -> None:
    collection = collection_factory(
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        inverted_index_config=Configure.inverted_index(index_timestamps=True),
    )
    if not collection._connection._weaviate_version.is_at_least(1, 23, 0):
        pytest.skip("filter by id is not supported in this version")

    obj1_uuid = collection.data.insert(properties={"name": "first"})
    obj2_uuid = collection.data.insert(properties={"name": "second"})

    obj2 = collection.query.fetch_object_by_id(uuid=obj2_uuid)
    assert obj2 is not None
    assert obj2.metadata is not None
    assert obj2.metadata.creation_time is not None

    filters = Filter.by_property(path).less_than(obj2.metadata.creation_time)
    objects = collection.query.fetch_objects(
        filters=filters, return_metadata=MetadataQuery(creation_time=True)
    ).objects

    assert len(objects) == 1
    assert objects[0].uuid == obj1_uuid


@pytest.mark.parametrize("filter_type", [Filter.by_creation_time(), Filter.by_update_time()])
def test_filter_timestamp_class(
    collection_factory: CollectionFactory,
    filter_type: Union[_FilterCreationTime, _FilterUpdateTime],
) -> None:
    collection = collection_factory(
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        inverted_index_config=Configure.inverted_index(index_timestamps=True),
    )
    if not collection._connection._weaviate_version.is_at_least(1, 23, 0):
        pytest.skip("filter by id is not supported in this version")

    obj1_uuid = collection.data.insert(properties={"name": "first"})
    obj2_uuid = collection.data.insert(properties={"name": "second"})

    obj1 = collection.query.fetch_object_by_id(uuid=obj1_uuid)
    assert obj1 is not None
    assert obj1.metadata is not None
    assert obj1.metadata.creation_time is not None

    obj2 = collection.query.fetch_object_by_id(uuid=obj2_uuid)
    assert obj2 is not None
    assert obj2.metadata is not None
    assert obj2.metadata.creation_time is not None

    filters = filter_type.less_than(obj2.metadata.creation_time)
    objects = collection.query.fetch_objects(
        filters=filters, return_metadata=MetadataQuery(creation_time=True)
    ).objects
    assert len(objects) == 1
    assert objects[0].uuid == obj1_uuid

    for filters in [
        filter_type.greater_than(obj1.metadata.creation_time),
        filter_type.not_equal(obj1.metadata.creation_time),
        filter_type.equal(obj2.metadata.creation_time),
    ]:
        objects = collection.query.fetch_objects(
            filters=filters, return_metadata=MetadataQuery(creation_time=True)
        ).objects
        assert len(objects) == 1
        assert objects[0].uuid == obj2_uuid

    for filters in [
        filter_type.contains_any([obj1.metadata.creation_time, obj2.metadata.creation_time]),
        filter_type.less_or_equal(obj2.metadata.creation_time),
        filter_type.greater_or_equal(obj1.metadata.creation_time),
    ]:
        objects = collection.query.fetch_objects(
            filters=filters, return_metadata=MetadataQuery(creation_time=True)
        ).objects

        uuids = [obj.uuid for obj in objects]
        assert len(uuids) == 2
        assert obj1_uuid in uuids and obj2_uuid in uuids


def test_time_update_and_creation_time(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        inverted_index_config=Configure.inverted_index(index_timestamps=True),
    )
    if not collection._connection._weaviate_version.is_at_least(1, 23, 0):
        pytest.skip("filter by id is not supported in this version")

    obj1_uuid = collection.data.insert(properties={"name": "first"})
    obj2_uuid = collection.data.insert(properties={"name": "second"})

    collection.data.update(uuid=obj1_uuid, properties={"name": "first updated"})

    obj1 = collection.query.fetch_object_by_id(uuid=obj1_uuid)
    assert obj1 is not None
    assert obj1.metadata is not None
    assert obj1.metadata.creation_time is not None
    assert obj1.metadata.last_update_time is not None
    assert obj1.metadata.creation_time < obj1.metadata.last_update_time

    filter_creation = Filter.by_update_time().less_than(obj1.metadata.creation_time)
    filter_update = Filter.by_update_time().less_than(obj1.metadata.last_update_time)

    objects_creation = collection.query.fetch_objects(
        filters=filter_creation, return_metadata=MetadataQuery(creation_time=True)
    ).objects
    assert len(objects_creation) == 0

    objects_update = collection.query.fetch_objects(
        filters=filter_update, return_metadata=MetadataQuery(creation_time=True)
    ).objects
    assert len(objects_update) == 1
    assert objects_update[0].uuid == obj2_uuid


def test_warning_old_filter(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuids = [
        collection.data.insert({"name": "Banana"}),
        collection.data.insert({"name": "Apple"}),
    ]
    with pytest.warns(DeprecationWarning):
        objects = collection.query.fetch_objects(filters=Filter("name").equal("Banana")).objects
    assert len(objects) == 1
    assert objects[0].uuid == uuids[0]

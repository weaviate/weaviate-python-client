import datetime
import uuid
from typing import List

import pytest as pytest

from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    Property,
    DataType,
    ReferenceProperty,
    Tokenization,
)
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.filters import (
    Filter,
    _FilterValue,
)
from weaviate.collections.classes.internal import ReferenceToMulti
from weaviate.collections.classes.tenants import Tenant
from weaviate.exceptions import (
    WeaviateQueryException,
)

NOW = datetime.datetime.now(datetime.timezone.utc)
LATER = NOW + datetime.timedelta(hours=1)
MUCH_LATER = NOW + datetime.timedelta(days=1)

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()


@pytest.mark.parametrize("verbose", [True, False])
def test_verbosity(collection_factory: CollectionFactory, verbose: bool) -> None:
    collection = collection_factory(vectorizer_config=Configure.Vectorizer.none())

    uuid1 = collection.data.insert(properties={})
    uuid2 = collection.data.insert(properties={})

    ret = collection.data.delete_many(
        where=Filter.by_id().equal(uuid1), verbose=verbose, dry_run=False
    )

    assert ret.failed == 0
    assert ret.matches == 1
    assert ret.successful == 1

    if verbose:
        assert ret.objects is not None
        assert len(ret.objects) == 1
        assert ret.objects[0].uuid == uuid1
        assert ret.objects[0].successful
        assert ret.objects[0].error is None
    else:
        assert ret.objects is None

    assert len(collection) == 1
    assert collection.query.fetch_object_by_id(uuid=uuid2) is not None


def test_batch_delete_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])

    uuid1 = collection.with_tenant("tenant1").data.insert(properties={})
    uuid2 = collection.with_tenant("tenant2").data.insert(properties={})

    with pytest.raises(WeaviateQueryException):
        collection.data.delete_many(where=Filter.by_id().contains_any([uuid1, uuid2]))

    ret = collection.with_tenant("tenant1").data.delete_many(
        where=Filter.by_id().contains_any([uuid1, uuid2])
    )
    assert ret.failed == 0
    assert ret.matches == 1
    assert ret.successful == 1

    assert len(collection.with_tenant("tenant1")) == 0
    assert len(collection.with_tenant("tenant2")) == 1


@pytest.mark.parametrize("dry_run", [True, False])
def test_dry_run(collection_factory: CollectionFactory, dry_run: bool) -> None:
    collection = collection_factory(vectorizer_config=Configure.Vectorizer.none())
    uuid1 = collection.data.insert(properties={})
    uuid2 = collection.data.insert(properties={})

    ret = collection.data.delete_many(where=Filter.by_id().equal(uuid1), dry_run=dry_run)

    assert ret.failed == 0
    assert ret.matches == 1
    assert ret.successful == 1
    assert ret.objects is None

    if dry_run:
        assert len(collection) == 2
        assert collection.query.fetch_object_by_id(uuid=uuid1) is not None
    else:
        assert len(collection) == 1
        assert collection.query.fetch_object_by_id(uuid=uuid1) is None

    assert collection.query.fetch_object_by_id(uuid=uuid2) is not None


def test_delete_by_time_metadata(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        inverted_index_config=Configure.inverted_index(index_timestamps=True),
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid1 = collection.data.insert(properties={})
    uuid2 = collection.data.insert(properties={})

    obj1 = collection.query.fetch_object_by_id(uuid=uuid1)

    collection.data.delete_many(
        where=Filter.by_creation_time().less_or_equal(obj1.metadata.creation_time)
    )

    assert len(collection) == 1
    assert collection.query.fetch_object_by_id(uuid=uuid2) is not None


def test_delete_many_or(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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

    collection.data.delete_many(
        where=Filter.by_property("age").equal(10) | Filter.by_property("age").equal(30)
    )
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["age"] == 20
    assert objects[0].properties["name"] == "Tim"


def test_delete_many_return(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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
    ret = collection.data.delete_many(where=Filter.by_property("name").equal("delet me"))
    assert ret.failed == 0
    assert ret.matches == 1
    assert ret.objects is None
    assert ret.successful == 1


def test_delete_many_and(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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
        where=Filter.by_property("age").equal(10) & Filter.by_property("name").equal("Timmy")
    )

    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["age"] == 10
    assert objects[0].properties["name"] == "Tommy"


@pytest.mark.parametrize(
    "properties,inserts,where,expected_len",
    [
        (
            [
                Property(name="text", data_type=DataType.TEXT),
            ],
            [
                DataObject(properties={"text": "text"}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("text").equal("text"),
            0,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
            ],
            [
                DataObject(properties={"text": "there is some text in here"}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("text").like("text"),
            0,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
            ],
            [
                DataObject(properties={"text": "banana"}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("text").like("ba*"),
            0,
        ),
        (
            [
                Property(name="texts", data_type=DataType.TEXT_ARRAY),
            ],
            [
                DataObject(properties={"texts": ["text1", "text2"]}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("texts").contains_all(["text1", "text2"]),
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
            Filter.by_property("texts").contains_any(["text1"]),
            1,
        ),
        (
            [Property(name="int", data_type=DataType.INT)],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("int").equal(10),
            0,
        ),
        (
            [
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("int").greater_than(5),
            0,
        ),
        (
            [
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("int").less_than(15),
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
            Filter.by_property("int").greater_or_equal(10),
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
            Filter.by_property("int").less_or_equal(10),
            0,
        ),
        (
            [
                Property(name="ints", data_type=DataType.INT_ARRAY),
            ],
            [
                DataObject(properties={"ints": [1, 2]}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("ints").contains_all([1, 2]),
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
            Filter.by_property("ints").contains_any([1]),
            1,
        ),
        (
            [
                Property(name="float", data_type=DataType.NUMBER),
            ],
            [
                DataObject(properties={"float": 1.0}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("float").equal(1.0),
            0,
        ),
        (
            [
                Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            ],
            [
                DataObject(properties={"floats": [1.0, 2.0]}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("floats").contains_all([1.0, 2.0]),
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
            Filter.by_property("floats").contains_any([1.0]),
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
            Filter.by_property("float").greater_than(
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
            Filter.by_property("bool").equal(True),
            1,
        ),
        (
            [
                Property(name="bools", data_type=DataType.BOOL_ARRAY),
            ],
            [
                DataObject(properties={"bools": [True, False]}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("bools").contains_all([True, False]),
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
            Filter.by_property("bools").contains_any([True]),
            1,
        ),
        (
            [
                Property(name="date", data_type=DataType.DATE),
            ],
            [
                DataObject(properties={"date": NOW}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("date").equal(NOW),
            0,
        ),
        (
            [
                Property(name="dates", data_type=DataType.DATE_ARRAY),
            ],
            [
                DataObject(properties={"dates": [NOW, LATER]}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("dates").contains_all([NOW, LATER]),
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
            Filter.by_property("dates").contains_any([NOW]),
            1,
        ),
        (
            [
                Property(name="uuid", data_type=DataType.UUID),
            ],
            [
                DataObject(properties={"uuid": UUID1}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("uuid").equal(UUID1),
            0,
        ),
        (
            [
                Property(name="uuids", data_type=DataType.UUID_ARRAY),
            ],
            [
                DataObject(properties={"uuids": [UUID1, UUID2]}, uuid=uuid.uuid4()),
            ],
            Filter.by_property("uuids").contains_all([UUID1, UUID2]),
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
            Filter.by_property("uuids").contains_any([UUID1]),
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
            Filter.by_property("text").equal("some name"),
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
            Filter.by_property("text").equal("some other name"),
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
            Filter.by_property("text").equal("money"),
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
            Filter.by_property("int").is_none(True),
            1,
        ),
        (
            [
                Property(name="text", data_type=DataType.TEXT),
                Property(name="int", data_type=DataType.INT),
            ],
            [
                DataObject(properties={"int": 10}, uuid=UUID1),
                DataObject(properties={"text": "I am ageless"}, uuid=UUID2),
            ],
            Filter.by_id().equal(UUID1),
            1,
        ),
    ],
)
def test_delete_many_simple(
    collection_factory: CollectionFactory,
    properties: List[Property],
    inserts: List[DataObject],
    where: _FilterValue,
    expected_len: int,
) -> None:
    collection = collection_factory(
        properties=properties,
        inverted_index_config=Configure.inverted_index(index_null_state=True),
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many(inserts)
    assert len(collection.query.fetch_objects().objects) == len(inserts)

    collection.data.delete_many(where=where)
    objects = collection.query.fetch_objects().objects
    assert len(objects) == expected_len


def test_batch_delete_with_refs(collection_factory: CollectionFactory) -> None:
    to = collection_factory(name="To")

    uuid_to1 = to.data.insert(properties={})
    uuid_to2 = to.data.insert(properties={})

    source = collection_factory(
        name="source", references=[ReferenceProperty(name="ref", target_collection=to.name)]
    )
    source.config.add_reference(
        ReferenceProperty.MultiTarget(name="ref_self", target_collections=[source.name, to.name])
    )

    uuid_source1 = source.data.insert(properties={})
    uuid_source2 = source.data.insert(properties={})
    source.data.reference_add(uuid_source1, from_property="ref", to=uuid_to1)
    source.data.reference_add(uuid_source2, "ref", to=uuid_to2)
    source.data.reference_add(
        uuid_source1,
        from_property="ref_self",
        to=ReferenceToMulti(uuids=uuid_source2, target_collection=source.name),
    )
    source.data.reference_add(
        uuid_source2,
        "ref_self",
        to=ReferenceToMulti(uuids=uuid_source1, target_collection=source.name),
    )

    ret = source.data.delete_many(
        where=Filter.by_ref_multi_target("ref_self", target_collection=source.name)
        .by_ref("ref")
        .by_id()
        .equal(uuid_to1),
        verbose=True,
    )
    assert ret.objects[0].uuid == uuid_source2


@pytest.mark.parametrize("update_or_creation", [True, False])
def test_delete_by_time_metadata_with_ref(
    collection_factory: CollectionFactory, update_or_creation: bool
) -> None:
    to = collection_factory(
        name="To", inverted_index_config=Configure.inverted_index(index_timestamps=True)
    )

    uuid_to1 = to.data.insert(properties={})
    uuid_to2 = to.data.insert(properties={})

    source = collection_factory(
        name="source", references=[ReferenceProperty(name="ref", target_collection=to.name)]
    )
    source.config.add_reference(
        ReferenceProperty.MultiTarget(name="ref_self", target_collections=[source.name, to.name])
    )

    uuid_source1 = source.data.insert(properties={})
    uuid_source2 = source.data.insert(properties={})
    source.data.reference_add(uuid_source1, from_property="ref", to=uuid_to1)
    source.data.reference_add(uuid_source2, "ref", to=uuid_to2)
    source.data.reference_add(
        uuid_source1,
        from_property="ref_self",
        to=ReferenceToMulti(uuids=uuid_source2, target_collection=source.name),
    )
    source.data.reference_add(
        uuid_source2,
        "ref_self",
        to=ReferenceToMulti(uuids=uuid_source1, target_collection=source.name),
    )

    obj1 = to.query.fetch_object_by_id(uuid=uuid_to1)

    if update_or_creation:
        source.data.delete_many(
            where=Filter.by_ref_multi_target("ref_self", target_collection=source.name)
            .by_ref("ref")
            .by_creation_time()
            .less_or_equal(obj1.metadata.creation_time)
        )
    else:
        source.data.delete_many(
            where=Filter.by_ref_multi_target("ref_self", target_collection=source.name)
            .by_ref(link_on="ref")
            .by_update_time()
            .less_or_equal(obj1.metadata.creation_time)
        )

    assert len(source) == 1
    assert source.query.fetch_object_by_id(uuid=uuid_source1) is not None
    assert source.query.fetch_object_by_id(uuid=uuid_source2) is None

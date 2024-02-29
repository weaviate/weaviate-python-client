import datetime
import io
import pathlib
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Sequence, TypedDict, Union

import pytest

from integration.conftest import CollectionFactory, CollectionFactoryGet, _sanitize_collection_name
from integration.constants import WEAVIATE_LOGO_OLD_ENCODED, WEAVIATE_LOGO_NEW_ENCODED
from weaviate.collections.classes.batch import ErrorObject
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
    Tokenization,
    Vectorizers,
    ConsistencyLevel,
)
from weaviate.collections.classes.data import (
    DataObject,
)
from weaviate.collections.classes.grpc import (
    QueryReference,
    HybridFusion,
    GroupBy,
    MetadataQuery,
    Move,
    Sort,
    _Sorting,
    PROPERTIES,
    PROPERTY,
    REFERENCE,
    NearMediaType,
)
from weaviate.collections.classes.internal import (
    _CrossReference,
    Object,
    ReferenceToMulti,
)
from weaviate.collections.classes.tenants import Tenant, TenantActivityStatus
from weaviate.collections.classes.types import PhoneNumber, WeaviateProperties
from weaviate.exceptions import (
    UnexpectedStatusCodeError,
    WeaviateInvalidInputError,
    WeaviateQueryError,
    WeaviateInsertInvalidPropertyError,
    WeaviateInsertManyAllFailedError,
)
from weaviate.types import UUID, UUIDS

UUID1 = uuid.UUID("806827e0-2b31-43ca-9269-24fa95a221f9")
UUID2 = uuid.UUID("8ad0d33c-8db1-4437-87f3-72161ca2a51a")
UUID3 = uuid.UUID("83d99755-9deb-4b16-8431-d1dff4ab0a75")

DATE1 = datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
DATE2 = datetime.datetime.strptime("2013-02-10", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
DATE3 = datetime.datetime.strptime("2019-06-10", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


def test_insert_with_typed_dict_generic(
    collection_factory: CollectionFactory,
    collection_factory_get: CollectionFactoryGet,
) -> None:
    class TestInsert(TypedDict):
        name: str

    dummy = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection = collection_factory_get(dummy.name, TestInsert)
    uuid = collection.data.insert(properties=TestInsert(name="some name"))
    objects = collection.query.fetch_objects()
    assert len(objects.objects) == 1
    name = collection.query.fetch_object_by_id(uuid).properties["name"]
    assert name == "some name"


def test_insert_with_dict_generic(
    collection_factory: CollectionFactory,
    collection_factory_get: CollectionFactoryGet,
) -> None:
    dummy = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection = collection_factory_get(dummy.name, Dict[str, str])
    uuid = collection.data.insert(properties={"name": "some name"})
    objects = collection.query.fetch_objects()
    assert len(objects.objects) == 1
    name = collection.query.fetch_object_by_id(uuid).properties["name"]
    assert name == "some name"


def test_insert_with_no_generic(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    objects = collection.query.fetch_objects()
    assert len(objects.objects) == 1
    prop = collection.query.fetch_object_by_id(uuid).properties["name"]
    assert prop == "some name"


def test_insert_with_consistency_level(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    ).with_consistency_level(ConsistencyLevel.ALL)
    uuid = collection.data.insert(properties={"name": "some name"})
    objects = collection.query.fetch_objects()
    assert len(objects.objects) == 1
    prop = collection.query.fetch_object_by_id(uuid).properties["name"]
    assert prop == "some name"


def test_insert_bad_input(collection_factory: CollectionFactory) -> None:
    collection = collection_factory()

    class BadInput:
        def __init__(self) -> None:
            self.name = "test"

    with pytest.raises(WeaviateInvalidInputError):
        collection.data.insert({"name": BadInput})


def test_delete_by_id(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid = collection.data.insert(properties={})
    assert collection.query.fetch_object_by_id(uuid) is not None
    assert collection.data.delete_by_id(uuid)
    assert collection.query.fetch_object_by_id(uuid) is None
    # does not exist anymore
    assert not collection.data.delete_by_id(uuid)


def test_delete_by_id_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create([Tenant(name="tenant1")])
    tenant1 = collection.with_tenant("tenant1")
    uuid = tenant1.data.insert(properties={})
    assert tenant1.query.fetch_object_by_id(uuid) is not None
    assert tenant1.data.delete_by_id(uuid)
    assert tenant1.query.fetch_object_by_id(uuid) is None
    # does not exist anymore
    assert not tenant1.data.delete_by_id(uuid)


def test_delete_by_id_consistency_level(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
    ).with_consistency_level(ConsistencyLevel.ALL)

    uuid = collection.data.insert(properties={})
    assert collection.query.fetch_object_by_id(uuid) is not None
    assert collection.data.delete_by_id(uuid)
    assert collection.query.fetch_object_by_id(uuid) is None
    # does not exist anymore
    assert not collection.data.delete_by_id(uuid)


@pytest.mark.parametrize(
    "objects,should_error",
    [
        (
            [
                DataObject(properties={"name": "some name"}, vector=[1, 2, 3]),
                DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
            ],
            False,
        ),
        (
            [
                {"name": "some name"},
                DataObject(properties={"name": "some other name"}),
            ],
            False,
        ),  # allowed at runtime but not by mypy, should it still be tested?
        (
            [
                {"name": "some name"},
                {"name": "some other name"},
            ],
            False,
        ),
        (
            [
                DataObject(properties={}),
                DataObject(properties={}, vector=[1, 2, 3]),
                DataObject(properties={}, uuid=uuid.uuid4()),
                DataObject(properties={}, vector=[1, 2, 3], uuid=uuid.uuid4()),
            ],
            False,
        ),
        (
            [
                {"name": "some name", "vector": [1, 2, 3]},
            ],
            True,
        ),
        (
            [
                {"name": "some name", "vector": [1, 2, 3]},
                DataObject(properties={"name": "some other name"}),
            ],
            True,
        ),
        (
            [
                {"name": "some name", "vector": [1, 2, 3]},
                DataObject(
                    properties={"name": "some other name"}, uuid=uuid.uuid4(), vector=[1, 2, 3]
                ),
            ],
            True,
        ),
        (
            [
                {"name": "some name", "id": uuid.uuid4()},
            ],
            True,
        ),
    ],
)
def test_insert_many(
    collection_factory: CollectionFactory,
    objects: Sequence[Union[WeaviateProperties, DataObject[WeaviateProperties, Any]]],
    should_error: bool,
) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    if not should_error:
        ret = collection.data.insert_many(objects)
        for idx, uuid_ in ret.uuids.items():
            obj1 = collection.query.fetch_object_by_id(uuid_)
            inserted = objects[idx]
            if isinstance(inserted, DataObject) and len(inserted.properties) == 0:
                if "name" in obj1.properties:  # change this when server version bumps to 1.24.0
                    assert obj1.properties["name"] is None
                else:
                    assert obj1.properties == {}
            elif isinstance(inserted, DataObject) and inserted.properties is not None:
                a = inserted.properties["name"]
                b = obj1.properties["name"]
                assert b == a
                # assert obj1.properties["name"] == inserted.properties["name"]
            else:
                assert not isinstance(inserted, DataObject)
                assert obj1.properties["name"] == inserted["name"]
    else:
        with pytest.raises(WeaviateInsertInvalidPropertyError) as e:
            collection.data.insert_many(objects)
        assert (
            e.value.message
            == f"""It is forbidden to insert `id` or `vector` inside properties: {objects[0]}. Only properties defined in your collection's config can be inserted as properties of the object, `id` is totally forbidden as it is reserved and `vector` is forbidden at this level. You should use the `DataObject` class if you wish to insert an object with a custom `vector` whilst inserting its properties."""
        )


def test_insert_many_all_error(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(True),
    )
    with pytest.raises(WeaviateInsertManyAllFailedError) as e:
        collection.data.insert_many([{"name": "steve"}, {"name": "bob"}, {"name": "joe"}])
    assert (
        e.value.message
        == f"Every object failed during insertion. Here is the set of all errors: class {collection.name} has multi-tenancy enabled, but request was without tenant"
    )


def test_insert_many_with_typed_dict(
    collection_factory: CollectionFactory,
    collection_factory_get: CollectionFactoryGet,
) -> None:
    class TestInsertManyWithTypedDict(TypedDict):
        name: str

    dummy = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection = collection_factory_get(dummy.name, TestInsertManyWithTypedDict)
    ret = collection.data.insert_many(
        [
            DataObject(properties=TestInsertManyWithTypedDict(name="some name"), vector=[1, 2, 3]),
            DataObject(
                properties=TestInsertManyWithTypedDict(name="some other name"), uuid=uuid.uuid4()
            ),
        ]
    )
    obj1 = collection.query.fetch_object_by_id(ret.uuids[0])
    obj2 = collection.query.fetch_object_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"


def test_insert_many_with_refs(collection_factory: CollectionFactory) -> None:
    ref_collection = collection_factory(
        name="target", vectorizer_config=Configure.Vectorizer.none()
    )
    uuid_to1 = ref_collection.data.insert(properties={})
    uuid_to2 = ref_collection.data.insert(properties={})

    collection = collection_factory(
        name="source",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[ReferenceProperty(name="ref_single", target_collection=ref_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.config.add_reference(
        ReferenceProperty.MultiTarget(
            name="ref_many", target_collections=[ref_collection.name, collection.name]
        )
    )
    uuid_from = collection.data.insert(properties={"name": "first"})

    ret = collection.data.insert_many(
        [
            DataObject(
                properties={
                    "name": "some name",
                },
                references={
                    "ref_single": [uuid_to1, uuid_to2],
                    "ref_many": ReferenceToMulti(
                        uuids=[uuid_from], target_collection=collection.name
                    ),
                },
                vector=[1, 2, 3],
            ),
            DataObject(
                properties={
                    "name": "some other name",
                },
                references={
                    "ref_single": uuid_to2,
                    "ref_many": ReferenceToMulti(
                        uuids=uuid_to1, target_collection=ref_collection.name
                    ),
                },
                uuid=uuid.uuid4(),
            ),
        ]
    )
    obj1 = collection.query.fetch_object_by_id(
        ret.uuids[0],
        return_properties=[
            "name",
        ],
        return_references=[
            QueryReference(link_on="ref_single"),
            QueryReference.MultiTarget(link_on="ref_many", target_collection=collection.name),
        ],
    )
    assert obj1 is not None
    assert obj1.properties["name"] == "some name"
    assert isinstance(obj1.references["ref_many"], _CrossReference)
    assert isinstance(obj1.references["ref_single"], _CrossReference)

    obj1 = collection.query.fetch_object_by_id(
        ret.uuids[1],
        return_properties=[
            "name",
        ],
        return_references=[
            QueryReference(link_on="ref_single"),
            QueryReference.MultiTarget(link_on="ref_many", target_collection=ref_collection.name),
        ],
    )
    assert obj1 is not None
    assert obj1.properties["name"] == "some other name"
    assert isinstance(obj1.references["ref_many"], _CrossReference)
    assert isinstance(obj1.references["ref_single"], _CrossReference)


def test_insert_many_error(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    ret = collection.data.insert_many(
        [
            DataObject(properties={"wrong_name": "some name"}, vector=[1, 2, 3]),
            DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
            DataObject(properties={"other_thing": "is_wrong"}, vector=[1, 2, 3]),
        ]
    )
    assert ret.has_errors

    obj = collection.query.fetch_object_by_id(ret.uuids[1])
    assert obj.properties["name"] == "some other name"

    assert len(ret.errors) == 2
    assert 0 in ret.errors and 2 in ret.errors

    assert isinstance(ret.all_responses[0], ErrorObject) and isinstance(
        ret.all_responses[2], ErrorObject
    )
    assert isinstance(ret.all_responses[1], uuid.UUID)


def test_insert_many_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    ret = tenant1.data.insert_many(
        [
            DataObject(properties={"name": "some name"}, vector=[1, 2, 3]),
            DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
        ]
    )
    assert not ret.has_errors
    obj1 = tenant1.query.fetch_object_by_id(ret.uuids[0])
    obj2 = tenant1.query.fetch_object_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"
    assert tenant2.query.fetch_object_by_id(ret.uuids[0]) is None
    assert tenant2.query.fetch_object_by_id(ret.uuids[1]) is None


def test_replace(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.replace(properties={"name": "other name"}, uuid=uuid)
    assert collection.query.fetch_object_by_id(uuid).properties["name"] == "other name"


@pytest.mark.parametrize("to_uuids", [UUID3, [UUID3]])
def test_replace_with_refs(collection_factory: CollectionFactory, to_uuids: UUIDS) -> None:
    ref_collection = collection_factory(
        name="target", vectorizer_config=Configure.Vectorizer.none()
    )
    ref_collection.data.insert(properties={}, uuid=UUID1)
    ref_collection.data.insert(properties={}, uuid=UUID2)
    ref_collection.data.insert(properties={}, uuid=UUID3)

    collection = collection_factory(
        name="source",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[ReferenceProperty(name="ref", target_collection=ref_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(
        properties={"name": "some name"},
        references={
            "ref": [UUID1, UUID2],
        },
    )

    collection.data.replace(
        properties={"name": "other name"},
        uuid=uuid,
        references={"ref": to_uuids},
    )
    obj = collection.query.fetch_object_by_id(
        uuid,
        return_properties=[
            "name",
        ],
        return_references=[
            QueryReference(link_on="ref"),
        ],
    )
    assert len(obj.references["ref"].objects) == 1
    assert obj.references["ref"].objects[0].uuid == UUID3


def test_replace_overwrites_vector(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"}, vector=[1, 2, 3])
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "some name"
    assert obj.vector["default"] == [1, 2, 3]

    collection.data.replace(properties={"name": "other name"}, uuid=uuid)
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "other name"
    assert "default" not in obj.vector

    collection.data.replace(properties={"name": "real name"}, uuid=uuid, vector=[2, 3, 4])
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "real name"
    assert obj.vector["default"] == [2, 3, 4]


def test_replace_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(properties={"name": "some name"})
    tenant1.data.replace(properties={"name": "other name"}, uuid=uuid)
    assert tenant1.query.fetch_object_by_id(uuid).properties["name"] == "other name"
    assert tenant2.query.fetch_object_by_id(uuid) is None


def test_update(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.update(properties={"name": "other name"}, uuid=uuid, vector=[1, 2, 3])
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "other name"
    assert obj.vector["default"] == [1, 2, 3]


def test_update_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(properties={"name": "some name"})
    tenant1.data.update(properties={"name": "other name"}, uuid=uuid)
    assert tenant1.query.fetch_object_by_id(uuid).properties["name"] == "other name"
    assert tenant2.query.fetch_object_by_id(uuid) is None


@pytest.mark.parametrize("to_uuids", [UUID3, [UUID3]])
def test_update_with_refs(collection_factory: CollectionFactory, to_uuids: UUIDS) -> None:
    ref_collection = collection_factory(
        name="target", vectorizer_config=Configure.Vectorizer.none()
    )
    ref_collection.data.insert(properties={}, uuid=UUID1)
    ref_collection.data.insert(properties={}, uuid=UUID2)
    ref_collection.data.insert(properties={}, uuid=UUID3)

    collection = collection_factory(
        name="source",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        references=[ReferenceProperty(name="ref", target_collection=ref_collection.name)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(
        properties={"name": "some name"},
        references={
            "ref": [UUID1, UUID2],
        },
    )

    collection.data.update(
        uuid=uuid,
        references={
            "ref": to_uuids,
        },
    )
    obj = collection.query.fetch_object_by_id(
        uuid,
        return_properties=[
            "name",
        ],
        return_references=[
            QueryReference(link_on="ref"),
        ],
    )
    assert len(obj.references["ref"].objects) == 3
    assert obj.references["ref"].objects[2].uuid == UUID3


@pytest.mark.parametrize(
    "data_type,value",
    [
        (DataType.TEXT, "1"),
        (DataType.INT, 1),
        (DataType.NUMBER, 0.5),
        (DataType.TEXT_ARRAY, ["1", "2"]),
        (DataType.INT_ARRAY, [1, 2]),
        (DataType.NUMBER_ARRAY, [1.0, 2.1]),
        (DataType.NUMBER_ARRAY, []),
    ],
)
def test_types(collection_factory: CollectionFactory, data_type: DataType, value: Any) -> None:
    name = "name"
    collection = collection_factory(
        properties=[Property(name=name, data_type=data_type)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_object = collection.data.insert(properties={name: value})

    object_get = collection.query.fetch_object_by_id(uuid_object)
    assert object_get is not None and object_get.properties[name] == value

    batch_return = collection.data.insert_many([{name: value}])
    assert not batch_return.has_errors

    object_get_from_batch = collection.query.fetch_object_by_id(batch_return.uuids[0])
    assert object_get_from_batch is not None and object_get_from_batch.properties[name] == value


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


@pytest.mark.parametrize("limit", [1, 2])
def test_bm25_limit(collection_factory: CollectionFactory, limit: int) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT, tokenization=Tokenization.WORD)],
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
    assert len(collection.query.bm25(query="test", limit=limit).objects) == limit


@pytest.mark.parametrize("offset,expected", [(0, 2), (1, 1), (2, 0)])
def test_bm25_offset(collection_factory: CollectionFactory, offset: int, expected: int) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT, tokenization=Tokenization.WORD)],
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

    assert len(collection.query.bm25(query="test", offset=offset).objects) == expected


@pytest.mark.parametrize("offset", [0, 1, 5])
def test_fetch_objects_offset(collection_factory: CollectionFactory, offset: int) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    nr_objects = 5
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.fetch_objects(offset=offset).objects
    assert len(objects) == nr_objects - offset


@pytest.mark.parametrize("limit", [1, 5])
def test_fetch_objects_limit(collection_factory: CollectionFactory, limit: int) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    for i in range(5):
        collection.data.insert({"Name": str(i)})

    assert len(collection.query.fetch_objects(limit=limit).objects) == limit


def test_search_after(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    nr_objects = 10
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.fetch_objects().objects
    for i, obj in enumerate(objects):
        objects_after = collection.query.fetch_objects(after=obj.uuid).objects
        assert len(objects_after) == nr_objects - 1 - i


def test_auto_limit(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
        inverted_index_config=Configure.inverted_index(),
    )
    for _ in range(4):
        collection.data.insert({"Name": "rain rain"})
    for _ in range(4):
        collection.data.insert({"Name": "rain"})
    for _ in range(4):
        collection.data.insert({"Name": ""})

    # match all objects with rain
    objects = collection.query.bm25(query="rain", auto_limit=0).objects
    assert len(objects) == 2 * 4
    objects = collection.query.hybrid(
        query="rain", auto_limit=0, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    ).objects
    assert len(objects) == 2 * 4

    # match only objects with two rains
    objects = collection.query.bm25(query="rain", auto_limit=1).objects
    assert len(objects) == 1 * 4
    objects = collection.query.hybrid(
        query="rain", auto_limit=1, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    ).objects
    assert len(objects) == 1 * 4


def test_query_properties(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Age", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert({"Name": "rain", "Age": 1})
    collection.data.insert({"Name": "sun", "Age": 2})
    collection.data.insert({"Name": "cloud", "Age": 3})
    collection.data.insert({"Name": "snow", "Age": 4})
    collection.data.insert({"Name": "hail", "Age": 5})

    objects = collection.query.bm25(query="rain", query_properties=["name"]).objects
    assert len(objects) == 1
    assert objects[0].properties["age"] == 1

    objects = collection.query.bm25(query="sleet", query_properties=["name"]).objects
    assert len(objects) == 0

    objects = collection.query.hybrid(query="cloud", query_properties=["name"], alpha=0).objects
    assert len(objects) == 1
    assert objects[0].properties["age"] == 3

    objects = collection.query.hybrid(query="sleet", query_properties=["name"], alpha=0).objects
    assert len(objects) == 0


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


def test_near_object(collection_factory: CollectionFactory) -> None:
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

    full_objects = collection.query.near_object(
        uuid_banana, return_metadata=MetadataQuery(distance=True, certainty=True)
    ).objects
    assert len(full_objects) == 4

    objects_distance = collection.query.near_object(
        uuid_banana, distance=full_objects[2].metadata.distance
    ).objects
    assert len(objects_distance) == 3

    objects_certainty = collection.query.near_object(
        uuid_banana, certainty=full_objects[2].metadata.certainty
    ).objects
    assert len(objects_certainty) == 3


def test_near_object_limit(collection_factory: CollectionFactory) -> None:
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

    banana = collection.query.fetch_object_by_id(uuid_banana)

    objs = collection.query.near_object(banana.uuid, limit=2).objects
    assert len(objs) == 2
    assert objs[0].uuid == uuid_banana
    assert objs[1].uuid == uuid_fruit


def test_near_object_offset(collection_factory: CollectionFactory) -> None:
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

    banana = collection.query.fetch_object_by_id(uuid_banana)

    objs = collection.query.near_object(banana.uuid, offset=1).objects
    assert len(objs) == 3
    assert objs[0].uuid == uuid_fruit


def test_near_object_group_by_argument(collection_factory: CollectionFactory) -> None:
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

    ret = collection.query.near_object(
        uuid_banana1,
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


def test_tenants(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(
            enabled=True,
        ),
    )

    collection.tenants.create([Tenant(name="tenant1")])

    tenants = collection.tenants.get()
    assert len(tenants) == 1
    assert type(tenants["tenant1"]) is Tenant
    assert tenants["tenant1"].name == "tenant1"

    collection.tenants.remove(["tenant1"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0


def test_multi_searches(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    collection.data.insert(properties={"name": "word"})
    collection.data.insert(properties={"name": "other"})

    objects = collection.query.bm25(
        query="word",
        return_properties=["name"],
        return_metadata=MetadataQuery(last_update_time=True),
    ).objects
    assert "name" in objects[0].properties
    assert objects[0].metadata.last_update_time is not None

    objects = collection.query.bm25(query="other").objects
    assert "name" in objects[0].properties
    assert objects[0].uuid is not None
    assert objects[0].metadata._is_empty()

    objects = collection.query.bm25(query="other", return_properties=[]).objects
    assert "name" not in objects[0].properties
    assert objects[0].uuid is not None
    assert objects[0].metadata._is_empty()


def test_search_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert({"name": "some name"})
    objects1 = tenant1.query.bm25(query="some").objects
    assert len(objects1) == 1
    assert objects1[0].uuid == uuid1

    objects2 = tenant2.query.bm25(query="some").objects
    assert len(objects2) == 0


def test_fetch_object_by_id_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")

    uuid1 = tenant1.data.insert({"name": "some name"})
    obj1 = tenant1.query.fetch_object_by_id(uuid1)
    assert obj1.properties["name"] == "some name"

    obj2 = tenant2.query.fetch_object_by_id(uuid1)
    assert obj2 is None

    uuid2 = tenant2.data.insert({"name": "some other name"})
    obj3 = tenant2.query.fetch_object_by_id(uuid2)
    assert obj3.properties["name"] == "some other name"

    obj4 = tenant1.query.fetch_object_by_id(uuid2)
    assert obj4 is None


def test_fetch_objects_with_limit(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    for i in range(10):
        collection.data.insert({"name": str(i)})

    objects = collection.query.fetch_objects(limit=5).objects
    assert len(objects) == 5


def test_fetch_objects_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")

    tenant1.data.insert({"name": "some name"})
    objects = tenant1.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "some name"

    objects = tenant2.query.fetch_objects().objects
    assert len(objects) == 0

    tenant2.data.insert({"name": "some other name"})
    objects = tenant2.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == "some other name"


def test_add_property(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )
    uuid1 = collection.data.insert({"name": "first"})
    collection.config.add_property(Property(name="number", data_type=DataType.INT))
    uuid2 = collection.data.insert({"name": "second", "number": 5})
    obj1 = collection.query.fetch_object_by_id(uuid1)
    obj2 = collection.query.fetch_object_by_id(uuid2)
    assert "name" in obj1.properties
    assert "name" in obj2.properties
    assert "number" in obj2.properties


def test_add_reference(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )
    uuid1 = collection.data.insert({"name": "first"})
    collection.config.add_reference(
        ReferenceProperty(name="self", target_collection=collection.name)
    )
    uuid2 = collection.data.insert({"name": "second"}, references={"self": uuid1})
    obj1 = collection.query.fetch_object_by_id(
        uuid1, return_properties=["name"], return_references=QueryReference(link_on="self")
    )
    obj2 = collection.query.fetch_object_by_id(
        uuid2, return_properties=["name"], return_references=QueryReference(link_on="self")
    )
    assert "name" in obj1.properties
    assert obj1.references == {}
    assert "name" in obj2.properties
    assert "self" in obj2.references


def test_collection_config_get(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    config = collection.config.get()
    assert config.name == collection.name
    assert len(config.properties) == 2
    assert config.properties[0].name == "name"
    assert config.properties[0].data_type == DataType.TEXT
    assert config.properties[1].name == "age"
    assert config.properties[1].data_type == DataType.INT
    assert config.vectorizer == Vectorizers.NONE


@pytest.mark.parametrize("return_properties", [None, [], ["name"]])
@pytest.mark.parametrize(
    "return_metadata",
    [
        None,
        [],
        MetadataQuery(),
        [
            "creation_time",
            "last_update_time",
            "distance",
            "certainty",
            "score",
            "explain_score",
            "is_consistent",
        ],
        MetadataQuery.full(),
    ],
)
@pytest.mark.parametrize("return_references", [None, [], [QueryReference(link_on="friend")]])
@pytest.mark.parametrize("include_vector", [False, True])
def test_return_properties_metadata_references_combos(
    collection_factory: CollectionFactory,
    return_properties: Optional[List[PROPERTY]],
    return_metadata: Optional[MetadataQuery],
    return_references: Optional[List[REFERENCE]],
    include_vector: bool,
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    collection.config.add_reference(
        ReferenceProperty(
            name="friend", target_collection=_sanitize_collection_name(collection.name)
        )
    )

    collection.data.insert(
        uuid=UUID1, properties={"name": "Graham", "age": 42}, vector=[1, 2, 3, 4]
    )
    collection.data.insert(
        uuid=UUID2,
        properties={"name": "John", "age": 43},
        vector=[1, 2, 3, 4],
        references={"friend": UUID1},
    )

    objects = collection.query.fetch_objects(
        include_vector=include_vector,
        return_properties=return_properties,
        return_metadata=return_metadata,
        return_references=return_references,
    ).objects

    obj = [obj for obj in objects if obj.uuid == UUID2][0]

    assert obj.uuid is not None

    if return_properties is None:
        assert "name" in obj.properties
        assert "age" in obj.properties
        assert obj.properties["name"] == "John"
        assert obj.properties["age"] == 43
    elif len(return_properties) == 0:
        assert "name" not in obj.properties
        assert "age" not in obj.properties
    else:
        assert "name" in obj.properties
        assert "age" not in obj.properties
        assert obj.properties["name"] == "John"

    if (
        return_metadata is None
        or return_metadata == MetadataQuery()
        or (isinstance(return_metadata, list) and len(return_metadata) == 0)
    ):
        assert obj.metadata._is_empty()
    else:
        assert obj.metadata.last_update_time is not None
        assert obj.metadata.creation_time is not None
        assert obj.metadata.explain_score is not None

    if include_vector:
        assert obj.vector["default"] == [1, 2, 3, 4]
    else:
        assert "default" not in obj.vector

    if return_references is None or len(return_references) == 0:
        assert obj.references is None
    else:
        assert obj.references is not None
        assert obj.references["friend"].objects[0].uuid == UUID1
        assert obj.references["friend"].objects[0].properties["name"] == "Graham"
        assert obj.references["friend"].objects[0].properties["age"] == 42


@pytest.mark.parametrize("hours,minutes,sign", [(0, 0, 1), (1, 20, -1), (2, 0, 1), (3, 40, -1)])
def test_insert_date_property(
    collection_factory: CollectionFactory, hours: int, minutes: int, sign: int
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="date", data_type=DataType.DATE)],
    )

    now = datetime.datetime.now(
        datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))
    )
    uuid = collection.data.insert(properties={"date": now})

    obj = collection.query.fetch_object_by_id(uuid)

    assert obj.properties["date"] == now
    # weaviate drops any trailing zeros from the microseconds part of the date
    # this means that the returned dates aren't in the ISO format and so cannot be parsed easily to datetime
    # moreover, UTC timezones specified as +-00:00 are converted to Z further complicating matters
    # as such the above line is a workaround to parse the date returned by weaviate, which may prove useful
    # when parsing the date property in generics and the ORM in the future


def test_exist(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid1 = collection.data.insert({})

    assert collection.data.exists(uuid1)
    assert not collection.data.exists(uuid.uuid4())


def test_exist_with_tenant(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])

    uuid1 = collection.with_tenant("Tenant1").data.insert({})
    uuid2 = collection.with_tenant("Tenant2").data.insert({})

    assert collection.with_tenant("Tenant1").data.exists(uuid1)
    assert not collection.with_tenant("Tenant2").data.exists(uuid1)
    assert collection.with_tenant("Tenant2").data.exists(uuid2)
    assert not collection.with_tenant("Tenant1").data.exists(uuid2)


def test_tenant_with_activity(collection_factory: CollectionFactory) -> None:
    name = "TestTenantActivity"
    collection = collection_factory(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create(
        [
            Tenant(name="1", activity_status=TenantActivityStatus.HOT),
            Tenant(name="2", activity_status=TenantActivityStatus.COLD),
            Tenant(name="3"),
        ]
    )
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT
    assert tenants["2"].activity_status == TenantActivityStatus.COLD
    assert tenants["3"].activity_status == TenantActivityStatus.HOT


def test_update_tenant(collection_factory: CollectionFactory) -> None:
    name = "TestUpdateTenant"
    collection = collection_factory(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )
    collection.tenants.create([Tenant(name="1", activity_status=TenantActivityStatus.HOT)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT

    collection.tenants.update([Tenant(name="1", activity_status=TenantActivityStatus.COLD)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.COLD


def test_return_list_properties(collection_factory: CollectionFactory) -> None:
    name_small = "TestReturnList"
    collection = collection_factory(
        name=name_small,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="strings", data_type=DataType.TEXT_ARRAY),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
            Property(name="uuids", data_type=DataType.UUID_ARRAY),
        ],
    )
    data: WeaviateProperties = {
        "ints": [1, 2, 3],
        "floats": [0.1, 0.4, 10.5],
        "strings": ["a", "list", "of", "strings"],
        "bools": [True, False, True],
        "dates": [
            datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(
                tzinfo=datetime.timezone.utc
            )
        ],
        "uuids": [uuid.uuid4(), uuid.uuid4()],
    }
    collection.data.insert(properties=data)
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties == data


@pytest.mark.parametrize("query", ["cake", ["cake"]])
@pytest.mark.parametrize("objects", [UUID1, str(UUID1), [UUID1], [str(UUID1)]])
@pytest.mark.parametrize("concepts", ["hiking", ["hiking"]])
@pytest.mark.parametrize(
    "return_properties", [["value"], None]
)  # Passing none here causes a server-side bug with <=1.22.2
def test_near_text(
    collection_factory: CollectionFactory,
    query: Union[str, List[str]],
    objects: Union[UUID, List[UUID]],
    concepts: Union[str, List[str]],
    return_properties: Optional[PROPERTIES],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        properties=[Property(name="value", data_type=DataType.TEXT)],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(properties={"value": "Apple"}, uuid=UUID1),
            DataObject(properties={"value": "Mountain climbing"}),
            DataObject(properties={"value": "apple cake"}),
            DataObject(properties={"value": "cake"}),
        ]
    )

    objs = collection.query.near_text(
        query=query,
        move_to=Move(force=1.0, objects=objects),
        move_away=Move(force=0.5, concepts=concepts),
        include_vector=True,
        return_properties=return_properties,
    ).objects

    assert len(objs) == 4

    assert objs[0].uuid == batch_return.uuids[2]
    assert "default" in objs[0].vector
    if return_properties is not None:
        assert objs[0].properties["value"] == "apple cake"


def test_near_text_error(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
    )

    with pytest.raises(ValueError):
        collection.query.near_text(query="test", move_to=Move(force=1.0))


def test_near_text_group_by_argument(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        properties=[Property(name="value", data_type=DataType.TEXT)],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(properties={"value": "Apple"}, uuid=UUID1),
            DataObject(properties={"value": "Mountain climbing"}),
            DataObject(properties={"value": "apple cake"}),
            DataObject(properties={"value": "cake"}),
        ]
    )

    ret = collection.query.near_text(
        query="cake",
        group_by=GroupBy(
            prop="value",
            number_of_groups=2,
            objects_per_group=100,
        ),
        include_vector=True,
        return_properties=["value"],
    )

    assert len(ret.objects) == 2
    assert ret.objects[0].uuid == batch_return.uuids[3]
    assert "default" in ret.objects[0].vector
    assert ret.objects[0].belongs_to_group == "cake"
    assert ret.objects[1].uuid == batch_return.uuids[2]
    assert "default" in ret.objects[1].vector
    assert ret.objects[1].belongs_to_group == "apple cake"


def test_near_text_limit(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        properties=[Property(name="value", data_type=DataType.TEXT)],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(properties={"value": "Apple"}, uuid=UUID1),
            DataObject(properties={"value": "Mountain climbing"}),
            DataObject(properties={"value": "apple cake"}),
            DataObject(properties={"value": "cake"}),
        ]
    )

    objects = collection.query.near_text(
        query="cake",
        limit=2,
        return_properties=["value"],
    ).objects

    assert len(objects) == 2
    assert objects[0].uuid == batch_return.uuids[3]
    assert objects[0].properties["value"] == "cake"
    assert objects[1].uuid == batch_return.uuids[2]
    assert objects[1].properties["value"] == "apple cake"


def test_near_text_offset(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        properties=[Property(name="value", data_type=DataType.TEXT)],
    )

    batch_return = collection.data.insert_many(
        [
            DataObject(properties={"value": "Apple"}, uuid=UUID1),
            DataObject(properties={"value": "Mountain climbing"}),
            DataObject(properties={"value": "apple cake"}),
            DataObject(properties={"value": "cake"}),
        ]
    )

    objects = collection.query.near_text(
        query="cake",
        offset=1,
        return_properties=["value"],
    ).objects

    assert len(objects) == 3
    assert objects[0].uuid == batch_return.uuids[2]
    assert objects[0].properties["value"] == "apple cake"


@pytest.mark.parametrize(
    "image_maker",
    [
        lambda: "./integration/weaviate-logo.png",
        lambda: WEAVIATE_LOGO_OLD_ENCODED,
        lambda: pathlib.Path("./integration/weaviate-logo.png"),
        lambda: pathlib.Path("./integration/weaviate-logo.png").open("rb"),
    ],
    ids=["path", "base64", "pathlib.Path", "io.BufferedReader"],
)
@pytest.mark.parametrize(
    "distance,certainty",
    [(None, None), (10.0, None), (None, 0.1)],
)
def test_near_image(
    collection_factory: CollectionFactory,
    image_maker: Callable[[], Union[str, pathlib.Path, io.BufferedReader]],
    distance: Optional[float],
    certainty: Optional[float],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["imageProp"]),
        properties=[
            Property(name="imageProp", data_type=DataType.BLOB),
        ],
    )

    uuid1 = collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_OLD_ENCODED})
    uuid2 = collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_NEW_ENCODED})

    image = image_maker()
    objects1 = collection.query.near_image(image, distance=distance, certainty=certainty).objects
    image = image_maker()  # need to reopen if file was consumed
    objects2 = collection.query.near_image(
        image, distance=distance, certainty=certainty, limit=1
    ).objects
    image = image_maker()  # need to reopen if file was consumed
    objects3 = collection.query.near_image(
        image, distance=distance, certainty=certainty, offset=1
    ).objects

    if isinstance(image, io.BufferedReader):
        image.close()

    assert len(objects1) == 2
    assert objects1[0].uuid == uuid1

    assert len(objects2) == 1
    assert objects2[0].uuid == uuid1

    assert len(objects3) == 1
    assert objects3[0].uuid == uuid2


@pytest.mark.parametrize(
    "image_maker",
    [
        lambda: "./integration/weaviate-logo.png",
        lambda: WEAVIATE_LOGO_OLD_ENCODED,
        lambda: pathlib.Path("./integration/weaviate-logo.png"),
        lambda: pathlib.Path("./integration/weaviate-logo.png").open("rb"),
    ],
    ids=["path", "base64", "pathlib.Path", "io.BufferedReader"],
)
@pytest.mark.parametrize(
    "distance,certainty",
    [(None, None), (10.0, None), (None, 0.1)],
)
def test_near_media(
    collection_factory: CollectionFactory,
    image_maker: Callable[[], Union[str, pathlib.Path, io.BufferedReader]],
    distance: Optional[float],
    certainty: Optional[float],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["imageProp"]),
        properties=[
            Property(name="imageProp", data_type=DataType.BLOB),
        ],
    )

    uuid1 = collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_OLD_ENCODED})
    uuid2 = collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_NEW_ENCODED})

    image = image_maker()
    objects1 = collection.query.near_media(
        image, NearMediaType.IMAGE, distance=distance, certainty=certainty
    ).objects
    image = image_maker()  # need to reopen if file was consumed
    objects2 = collection.query.near_media(
        image, NearMediaType.IMAGE, distance=distance, certainty=certainty, limit=1
    ).objects
    image = image_maker()  # need to reopen if file was consumed
    objects3 = collection.query.near_media(
        image, NearMediaType.IMAGE, distance=distance, certainty=certainty, offset=1
    ).objects

    if isinstance(image, io.BufferedReader):
        image.close()

    assert len(objects1) == 2
    assert objects1[0].uuid == uuid1

    assert len(objects2) == 1
    assert objects2[0].uuid == uuid1

    assert len(objects3) == 1
    assert objects3[0].uuid == uuid2


def test_bad_near_media_input(
    collection_factory: CollectionFactory,
) -> None:
    collection = collection_factory()

    with pytest.raises(WeaviateInvalidInputError):
        collection.query.near_media(42, NearMediaType.IMAGE).objects  # type: ignore


@pytest.mark.parametrize("which_case", [0, 1, 2, 3, 4])
def test_return_properties_with_query_specific_typed_dict(
    collection_factory: CollectionFactory, which_case: int
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
    )
    data: WeaviateProperties = {
        "int_": 1,
        "ints": [1, 2, 3],
    }
    collection.data.insert(properties=data)

    class DataModel0(TypedDict):
        int_: int

    class DataModel1(TypedDict):
        ints: List[int]

    class DataModel2(TypedDict):
        int_: int
        ints: List[int]

    class DataModel3(TypedDict):
        non_existant: str

    class DataModel4(TypedDict):
        pass

    objects: Union[
        List[Object[DataModel0, None]],
        List[Object[DataModel1, None]],
        List[Object[DataModel2, None]],
        List[Object[DataModel3, None]],
        List[Object[DataModel4, None]],
    ]
    if which_case == 0:
        objects = collection.query.fetch_objects(return_properties=DataModel0).objects
        assert len(objects) == 1
        assert objects[0].properties == {"int_": 1}
    elif which_case == 1:
        objects = collection.query.fetch_objects(return_properties=DataModel1).objects
        assert len(objects) == 1
        assert objects[0].properties == {"ints": [1, 2, 3]}
    elif which_case == 2:
        objects = collection.query.fetch_objects(return_properties=DataModel2).objects
        assert len(objects) == 1
        assert objects[0].properties == data
    elif which_case == 3:
        with pytest.raises(WeaviateQueryError):
            collection.query.fetch_objects(return_properties=DataModel3).objects
    elif which_case == 4:
        objects = collection.query.fetch_objects(return_properties=DataModel4).objects
        assert len(objects) == 1
        assert objects[0].properties == {}


def test_return_properties_with_general_typed_dict(collection_factory: CollectionFactory) -> None:
    class _Data(TypedDict):
        int_: int
        ints: List[int]

    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
        data_model_properties=_Data,
    )
    collection.data.insert(properties=_Data(int_=1, ints=[1, 2, 3]))
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["int_"] == 1
    assert objects[0].properties["ints"] == [1, 2, 3]


def test_return_properties_with_query_specific_typed_dict_overwriting_general_typed_dict(
    collection_factory: CollectionFactory,
) -> None:
    class _DataAll(TypedDict):
        int_: int
        ints: List[int]

    class _Data(TypedDict):
        int_: int

    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
        data_model_properties=_DataAll,
    )
    collection.data.insert(properties=_DataAll(int_=1, ints=[1, 2, 3]))
    objects = collection.query.fetch_objects(return_properties=_Data).objects
    assert len(objects) == 1
    assert objects[0].properties["int_"] == 1
    assert "ints" not in objects[0].properties

    obj = collection.query.fetch_object_by_id(objects[0].uuid, return_properties=_Data)
    assert obj is not None
    assert "ints" not in obj.properties
    assert obj.properties["int_"] == 1


def test_batch_with_arrays(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="texts", data_type=DataType.TEXT_ARRAY),
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="floats", data_type=DataType.NUMBER_ARRAY),
            Property(name="bools", data_type=DataType.BOOL_ARRAY),
            Property(name="uuids", data_type=DataType.UUID_ARRAY),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
        ],
    )

    objects_in = [
        DataObject[WeaviateProperties, None](
            {
                "texts": ["first", "second"],
                "ints": [1, 2],
                "floats": [1, 2],  # send floats as int
                "bools": [True, True, False],
                "dates": [DATE1, DATE3],
                "uuids": [UUID1, UUID3],
            }
        ),
        DataObject[WeaviateProperties, None](
            {
                "texts": ["third", "fourth"],
                "ints": [3, 4, 5],
                "floats": [1.2, 2],
                "bools": [False, False],
                "dates": [DATE2, DATE3, DATE1],
                "uuids": [UUID2, UUID1],
            }
        ),
    ]

    ret = collection.data.insert_many(objects_in)

    assert not ret.has_errors

    for i, obj_id in enumerate(ret.uuids.values()):
        obj_out = collection.query.fetch_object_by_id(obj_id)
        assert obj_out is not None

        for prop, val in objects_in[i].properties.items():
            assert obj_out.properties[prop] == val


@pytest.mark.parametrize(
    "sort,expected",
    [
        (Sort.by_property("name", True), [0, 1, 2]),
        (Sort.by_property("name", False), [2, 1, 0]),
        (Sort.by_property("age", False).by_property("name", True), [1, 2, 0]),
        (Sort.by_id(True), [0, 1, 2]),
        (Sort.by_id(False), [2, 1, 0]),
        (Sort.by_creation_time(True), [0, 1, 2]),
        (Sort.by_creation_time(False), [2, 1, 0]),
        (Sort.by_update_time(True), [0, 1, 2]),
        (Sort.by_update_time(False), [2, 1, 0]),
    ],
)
def test_sort(
    collection_factory: CollectionFactory,
    sort: _Sorting,
    expected: List[int],
) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="age", data_type=DataType.INT),
            Property(name="name", data_type=DataType.TEXT),
        ],
    )

    uuid1 = collection.data.insert(properties={"name": "A", "age": 20}, uuid=str(UUID1)[:-1] + "1")
    time.sleep(0.01)
    uuid2 = collection.data.insert(properties={"name": "B", "age": 22}, uuid=str(UUID1)[:-1] + "2")
    time.sleep(0.01)
    uuid3 = collection.data.insert(properties={"name": "C", "age": 22}, uuid=str(UUID1)[:-1] + "3")

    uuids_from = [uuid1, uuid2, uuid3]

    objects = collection.query.fetch_objects(sort=sort).objects
    assert len(objects) == len(expected)

    expected_uuids = [uuids_from[result] for result in expected]
    object_uuids = [obj.uuid for obj in objects]
    assert object_uuids == expected_uuids


def test_optional_ref_returns(collection_factory: CollectionFactory) -> None:
    ref_collection = collection_factory(
        name="target",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="text", data_type=DataType.TEXT)],
    )
    uuid_to1 = ref_collection.data.insert(properties={"text": "ref text"})

    collection = collection_factory(
        name="source",
        references=[
            ReferenceProperty(name="ref", target_collection=ref_collection.name),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert({}, references={"ref": uuid_to1})

    objects = collection.query.fetch_objects(
        return_references=[QueryReference(link_on="ref")]
    ).objects

    assert objects[0].references["ref"].objects[0].properties["text"] == "ref text"
    assert objects[0].references["ref"].objects[0].uuid is not None


@pytest.mark.parametrize("value", ["bob", ""])
def test_return_properties_with_type_hint_generic(
    collection_factory: CollectionFactory,
    collection_factory_get: CollectionFactoryGet,
    value: str,
) -> None:
    dummy = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    collection = collection_factory_get(dummy.name, Dict[str, str])
    collection.data.insert(properties={"name": value})
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["name"] == value


def test_return_blob_property(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="blob", data_type=DataType.BLOB),
        ]
    )
    uuid = collection.data.insert({"blob": WEAVIATE_LOGO_OLD_ENCODED})
    collection.data.insert_many([{"blob": WEAVIATE_LOGO_OLD_ENCODED}])
    obj = collection.query.fetch_object_by_id(uuid, return_properties=["blob"])
    objs = collection.query.fetch_objects(return_properties=["blob"]).objects
    assert len(objs) == 2
    assert obj.properties["blob"] == WEAVIATE_LOGO_OLD_ENCODED
    assert objs[0].properties["blob"] == WEAVIATE_LOGO_OLD_ENCODED
    assert objs[1].properties["blob"] == WEAVIATE_LOGO_OLD_ENCODED


def test_collection_shards(collection_factory: CollectionFactory) -> None:
    collection = collection_factory()
    shards = collection.shards()

    assert len(shards) == 1
    assert shards[0].collection == collection.name
    assert shards[0].name is not None
    assert shards[0].object_count == 0


def test_return_phone_number_property(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="phone", data_type=DataType.PHONE_NUMBER),
        ]
    )
    uuid1 = collection.data.insert({"phone": PhoneNumber(number="+441612345000")})
    uuid2 = collection.data.insert_many(
        [{"phone": PhoneNumber(default_country="GB", number="01612345000")}]
    ).uuids[0]
    obj1 = collection.query.fetch_object_by_id(uuid1, return_properties=["phone"])
    objs = collection.query.fetch_objects(return_properties=["phone"]).objects
    obj2 = [obj for obj in objs if obj.uuid == uuid2][0]
    assert len(objs) == 2
    assert obj1.properties["phone"].number == "+441612345000"
    assert obj1.properties["phone"].valid
    assert obj1.properties["phone"].international_formatted == "+44 161 234 5000"
    assert obj2.properties["phone"].number == "01612345000"
    assert obj2.properties["phone"].valid
    assert obj2.properties["phone"].international_formatted == "+44 161 234 5000"


def test_return_phone_number_property_wrong_type(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="phone", data_type=DataType.PHONE_NUMBER),
        ]
    )
    uuid1 = collection.data.insert({"phone": PhoneNumber(number="+441612345000")})
    obj1 = collection.query.fetch_object_by_id(uuid1)
    with pytest.raises(WeaviateInvalidInputError):
        uuid1 = collection.data.insert({"phone": obj1.properties["phone"]})


def test_double_insert_with_same_uuid(collection_factory: CollectionFactory) -> None:
    collection = collection_factory()
    uuid1 = collection.data.insert({})
    with pytest.raises(UnexpectedStatusCodeError):
        collection.data.insert({}, uuid=uuid1)


def test_nil_return(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="a", data_type=DataType.TEXT),
            Property(name="b", data_type=DataType.TEXT),
        ]
    )

    collection.data.insert({"a": "a1"})
    objs = collection.query.fetch_objects(return_properties=["a", "b"]).objects
    assert len(objs) == 1
    assert objs[0].properties["a"] == "a1"
    if "b" in objs[0].properties:  # change this when server version bumps to 1.24.0
        assert objs[0].properties["b"] is None


def test_none_query_hybrid_bm25(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )

    collection.data.insert({"text": "banana"})
    collection.data.insert({"text": "dog"})
    collection.data.insert({"text": "different concept"})

    hybrid_objs = collection.query.hybrid(
        query=None, vector=None, return_metadata=MetadataQuery.full()
    ).objects
    assert len(hybrid_objs) == 3
    assert all(obj.metadata.score is not None and obj.metadata.score == 0.0 for obj in hybrid_objs)

    bm25_objs = collection.query.bm25(query=None, return_metadata=MetadataQuery.full()).objects
    assert len(bm25_objs) == 3
    assert all(obj.metadata.score is not None and obj.metadata.score == 0.0 for obj in bm25_objs)

import datetime
import io
import pathlib
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Type, TypedDict, Union

import pytest
import weaviate

from pydantic import BaseModel
from pydantic.dataclasses import dataclass as pydantic_dataclass

from integration.constants import WEAVIATE_LOGO_OLD_ENCODED, WEAVIATE_LOGO_NEW_ENCODED
from weaviate.collections.classes.batch import ErrorObject

from weaviate.collections.collection import Collection
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    Vectorizer,
)
from weaviate.collections.classes.data import (
    DataObject,
)
from weaviate.collections.classes.grpc import (
    HybridFusion,
    FromReference,
    MetadataQuery,
    Move,
    Sort,
    PROPERTIES,
)
from weaviate.collections.classes.internal import Reference
from weaviate.collections.classes.tenants import Tenant, TenantActivityStatus
from weaviate.collections.classes.types import Properties
from weaviate.collections.data import _Data
from weaviate.collections.iterator import ITERATOR_CACHE_SIZE
from weaviate.exceptions import (
    InvalidDataModelException,
    WeaviateQueryException,
    WeaviateInsertInvalidPropertyError,
)
from weaviate.types import UUID

BEACON_START = "weaviate://localhost"

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()

DATE1 = datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
DATE2 = datetime.datetime.strptime("2013-02-10", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
DATE3 = datetime.datetime.strptime("2019-06-10", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


@pytest.fixture(scope="module")
def client():
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


def test_create_get_and_delete(client: weaviate.WeaviateClient):
    name = "TestCreateAndDeleteNoGeneric"
    col = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    assert client.collections.exists(name)
    assert isinstance(col, Collection)

    col = client.collections.get(name)
    assert isinstance(col, Collection)

    client.collections.delete(name)
    assert not client.collections.exists(name)


def test_delete_multiple(client: weaviate.WeaviateClient):
    name1 = "TestDeleteMultiple1"
    name2 = "TestDeleteMultiple2"
    client.collections.create(
        name=name1,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    client.collections.create(
        name=name2,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    assert client.collections.exists(name1)
    assert client.collections.exists(name2)

    client.collections.delete([name1, name2])
    assert not client.collections.exists(name1)
    assert not client.collections.exists(name2)


@pytest.mark.parametrize("use_typed_dict", [True, False])
def test_get_with_dict_generic(client: weaviate.WeaviateClient, use_typed_dict: bool):
    name = "TestGetWithDictGeneric"
    if use_typed_dict:

        class Right(TypedDict):
            name: str

        col = client.collections.get(name, Right)
    else:
        col = client.collections.get(name, Dict[str, str])
    assert isinstance(col, Collection)


def test_data_with_data_model_with_dict_generic(client: weaviate.WeaviateClient):
    name = "TestDataWithDictGeneric"

    class Right(TypedDict):
        name: str

    col = client.collections.get(name)
    assert isinstance(col, Collection)
    data = col.data.with_data_model(Right)
    assert isinstance(data, _Data)


WRONG_GENERIC_ERROR_MSG = "data_model can only be a dict type, e.g. Dict[str, str], or a class that inherits from TypedDict"


def test_get_with_empty_class_generic(client: weaviate.WeaviateClient):
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        client.collections.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_dataclass_generic(client: weaviate.WeaviateClient):
    @dataclass
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        client.collections.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_initialisable_class_generic(client: weaviate.WeaviateClient):
    class Wrong:
        name: str

        def __init__(self, name: str):
            self.name = name

    with pytest.raises(InvalidDataModelException) as error:
        client.collections.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_pydantic_class_generic(client: weaviate.WeaviateClient):
    class Wrong(BaseModel):
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        client.collections.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


def test_get_with_pydantic_dataclass_generic(client: weaviate.WeaviateClient):
    @pydantic_dataclass
    class Wrong:
        name: str

    with pytest.raises(InvalidDataModelException) as error:
        client.collections.get("NotImportant", Wrong)
    assert error.value.args[0] == WRONG_GENERIC_ERROR_MSG


@pytest.mark.parametrize(
    "which_generic",
    ["typed_dict", "dict", "none"],
)
def test_insert(client: weaviate.WeaviateClient, which_generic: str):
    name = "TestInsert"
    client.collections.delete(name)

    create_args = {
        "name": name,
        "properties": [Property(name="Name", data_type=DataType.TEXT)],
        "vectorizer_config": Configure.Vectorizer.none(),
    }

    class TestInsert(TypedDict):
        name: str

    insert_data = {"name": "some name"}
    if which_generic == "typed_dict":
        client.collections.create(**create_args)
        collection = client.collections.get(name, TestInsert)
        uuid = collection.data.insert(properties=TestInsert(**insert_data))
    elif which_generic == "dict":
        client.collections.create(**create_args)
        collection = client.collections.get(name, Dict[str, str])
        uuid = collection.data.insert(properties=insert_data)
    else:
        collection = client.collections.create(**create_args)
        uuid = collection.data.insert(properties=insert_data)
    name = collection.query.fetch_object_by_id(uuid).properties["name"]
    assert name == insert_data["name"]


def test_delete_by_id(client: weaviate.WeaviateClient):
    name = "TestDeleteById"
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    uuid = collection.data.insert(properties={"name": "some name"})
    assert collection.query.fetch_object_by_id(uuid) is not None
    collection.data.delete_by_id(uuid)
    assert collection.query.fetch_object_by_id(uuid) is None

    client.collections.delete(name)


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
        ),
        (
            [
                {"name": "some name"},
                {"name": "some other name"},
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
    client: weaviate.WeaviateClient,
    objects: List[Union[Properties, DataObject[Properties]]],
    should_error: bool,
):
    name = "TestInsertMany"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    if not should_error:
        ret = collection.data.insert_many(objects)
        for idx, uuid_ in ret.uuids.items():
            obj1 = collection.query.fetch_object_by_id(uuid_)
            assert (
                obj1.properties["name"] == objects[idx].properties["name"]
                if isinstance(objects[idx], DataObject)
                else objects[idx]["name"]
            )
    else:
        with pytest.raises(WeaviateInsertInvalidPropertyError) as e:
            collection.data.insert_many(objects)
        assert (
            e.value.message
            == f"""It is forbidden to insert `id` or `vector` inside properties: {objects[0]}. Only properties defined in your collection's config can be insterted as properties of the object, `id` is totally forbidden as it is reserved and `vector` is forbidden at this level. You should use the `DataObject` class if you wish to insert an object with a custom `vector` whilst inserting its properties."""
        )


def test_insert_many_with_typed_dict(client: weaviate.WeaviateClient):
    name = "TestInsertManyWithTypedDict"

    class TestInsertManyWithTypedDict(TypedDict):
        name: str

    client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection = client.collections.get(name, TestInsertManyWithTypedDict)
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

    client.collections.delete(name)


def test_insert_many_with_refs(client: weaviate.WeaviateClient):
    name_target = "RefClassBatchTarget"
    client.collections.delete(name_target)

    ref_collection = client.collections.create(
        name=name_target,
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_to1 = ref_collection.data.insert(properties={})
    uuid_to2 = ref_collection.data.insert(properties={})

    name = "TestInsertManyRefs"
    client.collections.delete(name)

    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref_single", target_collection=name_target),
            ReferencePropertyMultiTarget(name="ref_many", target_collections=[name_target, name]),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_from = collection.data.insert(properties={"name": "first"})

    ret = collection.data.insert_many(
        [
            DataObject(
                properties={
                    "name": "some name",
                    "ref_single": Reference.to(uuids=[uuid_to1, uuid_to2]),
                    "ref_many": Reference.to_multi_target(
                        uuids=uuid_from, target_collection=collection
                    ),
                },
                vector=[1, 2, 3],
            ),
            DataObject(
                properties={
                    "name": "some other name",
                    "ref_single": Reference.to(uuids=uuid_to2),
                    "ref_many": Reference.to_multi_target(
                        uuids=uuid_to1, target_collection=name_target
                    ),
                },
                uuid=uuid.uuid4(),
            ),
        ]
    )
    obj1 = collection.query.fetch_object_by_id(ret.uuids[0])
    assert obj1.properties["name"] == "some name"
    assert obj1.properties["ref_single"][0]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to1}"
    assert obj1.properties["ref_single"][1]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to2}"
    assert obj1.properties["ref_many"][0]["beacon"] == BEACON_START + f"/{name}/{uuid_from}"

    obj1 = collection.query.fetch_object_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some other name"
    assert obj1.properties["ref_single"][0]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to2}"
    assert obj1.properties["ref_many"][0]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to1}"


def test_insert_many_error(client: weaviate.WeaviateClient):
    name = "TestInsertManyWitHError"
    collection = client.collections.create(
        name=name,
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

    client.collections.delete(name)


def test_insert_many_with_tenant(client: weaviate.WeaviateClient):
    name = "TestInsertManyWithTenant"
    collection = client.collections.create(
        name=name,
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

    client.collections.delete(name)


def test_replace(client: weaviate.WeaviateClient):
    name = "TestReplace"
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.replace(properties={"name": "other name"}, uuid=uuid)
    assert collection.query.fetch_object_by_id(uuid).properties["name"] == "other name"

    client.collections.delete(name)


def test_replace_overwrites_vector(client: weaviate.WeaviateClient):
    name = "TestReplaceOverwritesVector"
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"}, vector=[1, 2, 3])
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "some name"
    assert obj.metadata.vector == [1, 2, 3]

    collection.data.replace(properties={"name": "other name"}, uuid=uuid)
    obj = collection.query.fetch_object_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "other name"
    assert obj.metadata.vector is None

    client.collections.delete(name)


def test_replace_with_tenant(client: weaviate.WeaviateClient):
    name = "TestReplaceWithTenant"
    collection = client.collections.create(
        name=name,
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

    client.collections.delete(name)


def test_update(client: weaviate.WeaviateClient):
    name = "TestUpdate"
    collection = client.collections.create(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.update(properties={"name": "other name"}, uuid=uuid)
    assert collection.query.fetch_object_by_id(uuid).properties["name"] == "other name"

    client.collections.delete(name)


def test_update_with_tenant(client: weaviate.WeaviateClient):
    name = "TestUpdateWithTenant"
    collection = client.collections.create(
        name=name,
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

    client.collections.delete(name)


@pytest.mark.parametrize(
    "data_type,value",
    [
        (DataType.TEXT, "1"),
        (DataType.INT, 1),
        (DataType.NUMBER, 0.5),
        (DataType.TEXT_ARRAY, ["1", "2"]),
        (DataType.INT_ARRAY, [1, 2]),
        (DataType.NUMBER_ARRAY, [1.0, 2.1]),
    ],
)
def test_types(client: weaviate.WeaviateClient, data_type: DataType, value):
    name = "name"
    collection = client.collections.create(
        name="Something",
        properties=[Property(name=name, data_type=data_type)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    uuid_object = collection.data.insert(properties={name: value})

    object_get = collection.query.fetch_object_by_id(uuid_object)
    assert object_get.properties[name] == value

    client.collections.delete("Something")


@pytest.mark.parametrize("fusion_type", [HybridFusion.RANKED, HybridFusion.RELATIVE_SCORE])
def test_search_hybrid(client: weaviate.WeaviateClient, fusion_type):
    collection = client.collections.create(
        name="Testing",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
    )
    collection.data.insert({"Name": "some name"}, uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid.uuid4())
    objs = collection.query.hybrid(alpha=0, query="name", fusion_type=fusion_type).objects
    assert len(objs) == 1
    client.collections.delete("Testing")


@pytest.mark.parametrize("limit", [1, 5])
def test_search_limit(client: weaviate.WeaviateClient, limit):
    collection = client.collections.create(
        name="TestLimit",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    for i in range(5):
        collection.data.insert({"Name": str(i)})

    assert len(collection.query.fetch_objects(limit=limit).objects) == limit

    client.collections.delete("TestLimit")


@pytest.mark.parametrize("offset", [0, 1, 5])
def test_search_offset(client: weaviate.WeaviateClient, offset):
    collection = client.collections.create(
        name="TestOffset",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    nr_objects = 5
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.fetch_objects(offset=offset).objects
    assert len(objects) == nr_objects - offset

    client.collections.delete("TestOffset")


def test_search_after(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestOffset",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    nr_objects = 10
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.fetch_objects(return_metadata=MetadataQuery(uuid=True)).objects
    for i, obj in enumerate(objects):
        objects_after = collection.query.fetch_objects(after=obj.metadata.uuid).objects
        assert len(objects_after) == nr_objects - 1 - i

    client.collections.delete("TestOffset")


def test_auto_limit(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestAutoLimit",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
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

    client.collections.delete("TestAutoLimit")


def test_query_properties(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestQueryProperties",
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

    client.collections.delete("TestQueryProperties")


def test_near_vector(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestNearVector",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.query.fetch_object_by_id(uuid_banana, include_vector=True)

    full_objects = collection.query.near_vector(
        banana.metadata.vector, return_metadata=MetadataQuery(distance=True, certainty=True)
    ).objects
    assert len(full_objects) == 4

    objects_distance = collection.query.near_vector(
        banana.metadata.vector, distance=full_objects[2].metadata.distance
    ).objects
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_vector(
        banana.metadata.vector, certainty=full_objects[2].metadata.certainty
    ).objects
    assert len(objects_distance) == 3

    client.collections.delete("TestNearVector")


def test_near_vector_group_by(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestNearVectorGroupBy",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Count", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
    )
    uuid_banana1 = collection.data.insert({"Name": "Banana", "Count": 51})
    collection.data.insert({"Name": "Banana", "Count": 72})
    collection.data.insert({"Name": "car", "Count": 12})
    collection.data.insert({"Name": "Mountain", "Count": 1})

    banana1 = collection.query.fetch_object_by_id(uuid_banana1, include_vector=True)

    assert banana1.metadata.vector is not None
    ret = collection.query_group_by.near_vector(
        banana1.metadata.vector,
        group_by_property="name",
        number_of_groups=4,
        objects_per_group=10,
        return_metadata=MetadataQuery(distance=True, certainty=True),
    )

    assert len(ret.objects) == 4
    assert ret.objects[0].belongs_to_group == "Banana"
    assert ret.objects[1].belongs_to_group == "Banana"
    assert ret.objects[2].belongs_to_group == "car"
    assert ret.objects[3].belongs_to_group == "Mountain"

    client.collections.delete("TestNearVector")


def test_near_object(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestNearObject",
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
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

    client.collections.delete("TestNearObject")


def test_near_object_group_by(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestNearObjectGroupBy",
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            Property(name="Count", data_type=DataType.INT),
        ],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
    )
    uuid_banana1 = collection.data.insert({"Name": "Banana", "Count": 51})
    collection.data.insert({"Name": "Banana", "Count": 72})
    collection.data.insert({"Name": "car", "Count": 12})
    collection.data.insert({"Name": "Mountain", "Count": 1})

    ret = collection.query_group_by.near_object(
        uuid_banana1,
        group_by_property="name",
        number_of_groups=4,
        objects_per_group=10,
        return_metadata=MetadataQuery(distance=True, certainty=True),
    )

    assert len(ret.objects) == 4
    assert ret.objects[0].belongs_to_group == "Banana"
    assert ret.objects[1].belongs_to_group == "Banana"
    assert ret.objects[2].belongs_to_group == "car"
    assert ret.objects[3].belongs_to_group == "Mountain"

    client.collections.delete("TestNearObject")


def test_tenants(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="Tenants",
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

    client.collections.delete("Tenants")


def test_multi_searches(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestMultiSearches",
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    collection.data.insert(properties={"name": "word"})
    collection.data.insert(properties={"name": "other"})

    objects = collection.query.bm25(
        query="word",
        return_properties=["name"],
        return_metadata=MetadataQuery(last_update_time_unix=True),
    ).objects
    assert "name" in objects[0].properties
    assert objects[0].metadata.last_update_time_unix is not None

    objects = collection.query.bm25(query="other", return_metadata=MetadataQuery(uuid=True)).objects
    assert "name" not in objects[0].properties
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.last_update_time_unix is None

    client.collections.delete("TestMultiSearches")


def test_search_with_tenant(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestTenantSearch",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert({"name": "some name"})
    objects1 = tenant1.query.bm25(query="some", return_metadata=MetadataQuery(uuid=True)).objects
    assert len(objects1) == 1
    assert objects1[0].metadata.uuid == uuid1

    objects2 = tenant2.query.bm25(query="some", return_metadata=MetadataQuery(uuid=True)).objects
    assert len(objects2) == 0

    client.collections.delete("TestTenantSearch")


def test_fetch_object_by_id_with_tenant(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestTenantGet",
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

    client.collections.delete("TestTenantGet")


def test_fetch_objects_with_limit(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestLimit",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    for i in range(10):
        collection.data.insert({"name": str(i)})

    objects = collection.query.fetch_objects(limit=5).objects
    assert len(objects) == 5

    client.collections.delete("TestLimit")


def test_fetch_objects_with_tenant(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestTenantGetWithTenant",
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

    client.collections.delete("TestTenantGetWithTenant")


def test_add_property(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestAddProperty",
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

    client.collections.delete("TestAddProperty")


def test_collection_config_get(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionSchemaGet",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    config = collection.config.get()
    assert config.name == "TestCollectionSchemaGet"
    assert len(config.properties) == 2
    assert config.properties[0].name == "name"
    assert config.properties[0].data_type == DataType.TEXT
    assert config.properties[1].name == "age"
    assert config.properties[1].data_type == DataType.INT
    assert config.vectorizer == Vectorizer.NONE

    client.collections.delete("TestCollectionSchemaGet")


def test_empty_search_returns_everything(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestReturnEverything",
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    collection.data.insert(properties={"name": "word"})

    objects = collection.query.bm25(query="word").objects
    assert "name" in objects[0].properties
    assert objects[0].properties["name"] == "word"
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.score is not None
    assert objects[0].metadata.last_update_time_unix is not None
    assert objects[0].metadata.creation_time_unix is not None
    assert objects[0].metadata.vector is None

    client.collections.delete("TestReturnEverything")


@pytest.mark.parametrize("hours,minutes,sign", [(0, 0, 1), (1, 20, -1), (2, 0, 1), (3, 40, -1)])
def test_insert_date_property(client: weaviate.WeaviateClient, hours: int, minutes: int, sign: int):
    client.collections.delete("TestInsertDateProperty")
    collection = client.collections.create(
        name="TestInsertDateProperty",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="date", data_type=DataType.DATE)],
    )

    now = datetime.datetime.now(
        datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))
    )
    uuid = collection.data.insert(properties={"date": now})

    obj = collection.query.fetch_object_by_id(uuid)

    assert (
        datetime.datetime.strptime(
            "".join(
                obj.properties["date"].rsplit(":", 1)
                if obj.properties["date"][-1] != "Z"
                else obj.properties["date"]
            ),
            "%Y-%m-%dT%H:%M:%S.%f%z",
        )
        == now
    )
    # weaviate drops any trailing zeros from the microseconds part of the date
    # this means that the returned dates aren't in the ISO format and so cannot be parsed easily to datetime
    # moreover, UTC timezones specified as +-00:00 are converted to Z further complicating matters
    # as such the above line is a workaround to parse the date returned by weaviate, which may prove useful
    # when parsing the date property in generics and the ORM in the future

    client.collections.delete("TestInsertDateProperty")


def test_collection_name_capitalization(client: weaviate.WeaviateClient):
    name_small = "collectionCapitalizationTest"
    name_big = "CollectionCapitalizationTest"
    collection = client.collections.create(
        name=name_small,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    assert collection.name == name_big
    client.collections.delete(name_small)
    assert not client.collections.exists(name_small)
    assert not client.collections.exists(name_big)


def test_tenant_with_activity(client: weaviate.WeaviateClient):
    name = "TestTenantActivity"
    collection = client.collections.create(
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


def test_update_tenant(client: weaviate.WeaviateClient):
    name = "TestUpdateTenant"
    collection = client.collections.create(
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


def test_return_list_properties(client: weaviate.WeaviateClient):
    name_small = "TestReturnList"
    collection = client.collections.create(
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
    data = {
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

    # remove dates because of problems comparing dates
    dates_from_weaviate = objects[0].properties.pop("dates")
    dates2 = [datetime.datetime.fromisoformat(date) for date in dates_from_weaviate]
    dates = data.pop("dates")
    assert dates2 == dates

    # remove uuids because weaviate returns them as strings
    uuids_from_weaviate = objects[0].properties.pop("uuids")
    uuids2 = [uuid.UUID(uuids) for uuids in uuids_from_weaviate]
    uuids = data.pop("uuids")
    assert uuids2 == uuids

    assert objects[0].properties == data


@pytest.mark.parametrize("query", ["cake", ["cake"]])
@pytest.mark.parametrize("objects", [UUID1, str(UUID1), [UUID1], [str(UUID1)]])
@pytest.mark.parametrize("concepts", ["hiking", ["hiking"]])
@pytest.mark.parametrize(
    "return_properties", [["value"], None]
)  # Passing none here causes a server-side bug with <=1.22.2
def test_near_text(
    client: weaviate.WeaviateClient,
    query: Union[str, List[str]],
    objects: Union[UUID, List[UUID]],
    concepts: Union[str, List[str]],
    return_properties: Optional[PROPERTIES],
):
    name = "TestNearText"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
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
        return_metadata=MetadataQuery(uuid=True, vector=True),
        return_properties=return_properties,
    ).objects

    assert len(objs) == 4

    assert objs[0].metadata.uuid == batch_return.uuids[2]
    assert objs[0].metadata.vector is not None
    if return_properties is not None:
        assert objs[0].properties["value"] == "apple cake"


def test_near_text_error(client: weaviate.WeaviateClient):
    name = "TestNearTextError"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
    )

    with pytest.raises(ValueError):
        collection.query.near_text(query="test", move_to=Move(force=1.0))


def test_near_text_group_by(client: weaviate.WeaviateClient):
    name = "TestNearTextGroupBy"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
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

    ret = collection.query_group_by.near_text(
        query="cake",
        group_by_property="value",
        number_of_groups=2,
        objects_per_group=100,
        return_metadata=MetadataQuery(uuid=True, vector=True),
        return_properties=["value"],
    )

    assert len(ret.objects) == 2
    assert ret.objects[0].metadata.uuid == batch_return.uuids[2]
    assert ret.objects[0].metadata.vector is not None
    assert ret.objects[0].belongs_to_group == "apple cake"
    assert ret.objects[1].metadata.uuid == batch_return.uuids[3]
    assert ret.objects[1].metadata.vector is not None
    assert ret.objects[1].belongs_to_group == "cake"


def test_near_text_limit(client: weaviate.WeaviateClient):
    name = "TestNearTextLimit"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(),
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
        return_metadata=MetadataQuery(uuid=True),
        return_properties=["value"],
    ).objects

    assert len(objects) == 2
    assert objects[0].metadata.uuid == batch_return.uuids[2]
    assert objects[0].properties["value"] == "apple cake"
    assert objects[1].metadata.uuid == batch_return.uuids[3]
    assert objects[1].properties["value"] == "cake"


@pytest.mark.parametrize(
    "image_maker",
    [
        lambda: WEAVIATE_LOGO_OLD_ENCODED,
        lambda: pathlib.Path("./integration/weaviate-logo.png"),
        lambda: pathlib.Path("./integration/weaviate-logo.png").open("rb"),
    ],
    ids=["base64", "pathlib.Path", "io.BufferedReader"],
)
@pytest.mark.parametrize(
    "distance,certainty",
    [(None, None), (10, None), (None, 0.1)],
)
def test_near_image(
    client: weaviate.WeaviateClient,
    image_maker: Callable[[], Union[str, pathlib.Path, io.BufferedReader]],
    distance: Optional[float],
    certainty: Optional[float],
):
    name = "TestNearImage"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.img2vec_neural(image_fields=["imageProp"]),
        properties=[
            Property(name="imageProp", data_type=DataType.BLOB),
        ],
    )

    uuid1 = collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_OLD_ENCODED})
    collection.data.insert(properties={"imageProp": WEAVIATE_LOGO_NEW_ENCODED})

    image = image_maker()
    objects = collection.query.near_image(image, distance=distance, certainty=certainty).objects

    if isinstance(image, io.BufferedReader):
        image.close()

    assert len(objects) == 2
    assert objects[0].metadata.uuid == uuid1


@pytest.mark.parametrize("which_case", [0, 1, 2, 3])
def test_return_properties_with_query_specific_typed_dict(
    client: weaviate.WeaviateClient, which_case: int
):
    name = "TestReturnListWithModel"
    client.collections.delete(name)
    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
    )
    data = {
        "int_": 1,
        "ints": [1, 2, 3],
    }
    collection.data.insert(properties=data)
    if which_case == 0:

        class DataModel(TypedDict):
            int_: int

        objects = collection.query.fetch_objects(return_properties=DataModel).objects
        assert len(objects) == 1
        assert objects[0].properties == {"int_": 1}
    elif which_case == 1:

        class DataModel(TypedDict):
            ints: List[int]

        objects = collection.query.fetch_objects(return_properties=DataModel).objects
        assert len(objects) == 1
        assert objects[0].properties == {"ints": [1, 2, 3]}
    elif which_case == 2:

        class DataModel(TypedDict):
            int_: int
            ints: List[int]

        objects = collection.query.fetch_objects(return_properties=DataModel).objects
        assert len(objects) == 1
        assert objects[0].properties == data
    elif which_case == 3:

        class DataModel(TypedDict):
            non_existant: str

        with pytest.raises(WeaviateQueryException):
            collection.query.fetch_objects(return_properties=DataModel).objects


def test_return_properties_with_general_typed_dict(client: weaviate.WeaviateClient):
    name = "TestReturnListWithModel"
    client.collections.delete(name)

    class _Data(TypedDict):
        int_: int
        ints: List[int]

    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
        data_model=_Data,
    )
    collection.data.insert(properties=_Data(int_=1, ints=[1, 2, 3]))
    objects = collection.query.fetch_objects().objects
    assert len(objects) == 1
    assert objects[0].properties["int_"] == 1
    assert objects[0].properties["ints"] == [1, 2, 3]


def test_return_properties_with_query_specific_typed_dict_overwriting_general_typed_dict(
    client: weaviate.WeaviateClient,
):
    name = "TestReturnListWithModel"
    client.collections.delete(name)

    class _DataAll(TypedDict):
        int_: int
        ints: List[int]

    class _Data(TypedDict):
        int_: int

    collection = client.collections.create(
        name=name,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="int_", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
        ],
        data_model=_DataAll,
    )
    collection.data.insert(properties=_DataAll(int_=1, ints=[1, 2, 3]))
    objects = collection.query.fetch_objects(return_properties=_Data).objects
    assert len(objects) == 1
    assert objects[0].properties["int_"] == 1
    assert "ints" not in objects[0].properties


def test_batch_with_arrays(client: weaviate.WeaviateClient):
    client.collections.delete("TestBatchArrays")
    collection = client.collections.create(
        name="TestBatchArrays",
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

    objects_in: List[DataObject] = [
        DataObject(
            {
                "texts": ["first", "second"],
                "ints": [1, 2],
                "floats": [1, 2],  # send floats as int
                "bools": [True, True, False],
                "dates": [DATE1, DATE3],
                "uuids": [UUID1, UUID3],
            }
        ),
        DataObject(
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

        for prop, val in objects_in[i].properties.items():
            if prop == "dates":
                dates_from_weaviate = [
                    datetime.datetime.fromisoformat(date) for date in obj_out.properties[prop]
                ]
                assert val == dates_from_weaviate
            elif prop == "uuids":
                uuids_from_weaviate = [uuid.UUID(prop) for prop in obj_out.properties[prop]]
                assert val == uuids_from_weaviate
            else:
                assert obj_out.properties[prop] == val


@pytest.mark.parametrize(
    "sort,expected",
    [
        (Sort(prop="name", ascending=True), [0, 1, 2]),
        (Sort(prop="name", ascending=False), [2, 1, 0]),
        ([Sort(prop="age", ascending=False), Sort(prop="name", ascending=True)], [1, 2, 0]),
    ],
)
def test_sort(client: weaviate.WeaviateClient, sort: Union[Sort, List[Sort]], expected: List[int]):
    name = "TestSort"
    client.collections.delete(name)

    collection = client.collections.create(
        name="TestSort",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="age", data_type=DataType.INT),
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    uuids_from = [
        collection.data.insert(properties={"name": "A", "age": 20}),
        collection.data.insert(properties={"name": "B", "age": 22}),
        collection.data.insert(properties={"name": "C", "age": 22}),
    ]

    objects = collection.query.fetch_objects(sort=sort).objects
    assert len(objects) == len(expected)

    expected_uuids = [uuids_from[result] for result in expected]
    object_uuids = [obj.metadata.uuid for obj in objects]
    assert object_uuids == expected_uuids


def test_optional_ref_returns(client: weaviate.WeaviateClient):
    name_target = "TestRefReturnEverything"
    name = "TestInsertManyRefs"
    client.collections.delete(name_target)
    client.collections.delete(name)

    ref_collection = client.collections.create(
        name=name_target,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[Property(name="text", data_type=DataType.TEXT)],
    )
    uuid_to1 = ref_collection.data.insert(properties={"text": "ref text"})

    collection = client.collections.create(
        name=name,
        properties=[
            ReferenceProperty(name="ref", target_collection=name_target),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert(properties={"ref": Reference.to(uuid_to1)})

    objects = collection.query.fetch_objects(
        return_properties=[FromReference(link_on="ref")]
    ).objects

    assert objects[0].properties["ref"].objects[0].properties["text"] == "ref text"
    assert objects[0].properties["ref"].objects[0].metadata.uuid is not None


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
def test_iterator(client: weaviate.WeaviateClient, count: int):
    name = "TestIterator"
    client.collections.delete(name)

    collection = client.collections.create(
        name=name,
        properties=[Property(name="data", data_type=DataType.INT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    if count > 0:
        collection.data.insert_many([DataObject(properties={"data": i}) for i in range(count)])

    # make sure a new iterator resets the internal state
    for _ in range(3):
        # get the property and sort them - order returned by weaviate is not identical to the order inserted
        all_data: list[int] = sorted([int(obj.properties["data"]) for obj in collection.iterator()])
        assert all_data == list(range(count))


class Data(TypedDict):
    data: int


@pytest.mark.parametrize(
    "return_metadata",
    [None, MetadataQuery(creation_time_unix=True)],
)
@pytest.mark.parametrize(
    "return_properties",
    [None, Data, ["data"]],
)
def test_iterator_arguments(
    client: weaviate.WeaviateClient,
    return_metadata: Optional[MetadataQuery],
    return_properties: Optional[Union[PROPERTIES, Type[Properties]]],
):
    name = "TestIteratorTypedDict"
    client.collections.delete(name)

    collection = client.collections.create(
        name=name,
        properties=[Property(name="data", data_type=DataType.INT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    collection.data.insert_many([DataObject(properties={"data": i}) for i in range(10)])

    iter_ = collection.iterator(
        return_metadata=return_metadata, return_properties=return_properties
    )

    # Expect everything back
    if return_metadata is None and return_properties is None:
        all_data: list[int] = sorted([int(obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all(obj.metadata.creation_time_unix is not None for obj in iter_)
        assert all(obj.metadata.score is not None for obj in iter_)
    # Expect only metadata with only creation_time_unix
    elif return_metadata is not None and return_properties is None:
        assert all(obj.properties == {} for obj in iter_)
        assert all(obj.metadata.creation_time_unix is not None for obj in iter_)
        assert all(obj.metadata.score is None for obj in iter_)
    # Expect only properties
    elif return_metadata is None and return_properties is not None:
        all_data: list[int] = sorted([int(obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all(obj.metadata.creation_time_unix is None for obj in iter_)
    # Expect properties and metadata with only creation_time_unix
    else:
        all_data: list[int] = sorted([int(obj.properties["data"]) for obj in iter_])
        assert all_data == list(range(10))
        assert all(obj.metadata.creation_time_unix is not None for obj in iter_)
        assert all(obj.metadata.score is None for obj in iter_)


def test_iterator_dict_hint(client: weaviate.WeaviateClient):
    name = "TestIteratorTypedDict"
    client.collections.delete(name)

    collection = client.collections.create(
        name=name,
        properties=[Property(name="data", data_type=DataType.INT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )

    collection.data.insert_many([DataObject(properties={"data": i}) for i in range(10)])

    with pytest.raises(TypeError) as e:
        for _ in collection.iterator(return_properties=dict):
            pass
    assert (
        "return_properties must only be a TypedDict or PROPERTIES within this context but is "
        in e.value.args[0]
    )


def test_iterator_with_default_generic(client: weaviate.WeaviateClient):
    name = "TestIteratorWithDefaultGeneric"
    client.collections.delete(name)

    class This(TypedDict):
        this: str

    class That(TypedDict):
        this: str
        that: str

    collection = client.collections.create(
        name=name,
        properties=[
            Property(name="this", data_type=DataType.TEXT),
            Property(name="that", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        data_model=That,
    )

    collection.data.insert_many(
        [DataObject(properties=That(this="this", that="that")) for _ in range(10)]
    )

    iter_ = collection.iterator()
    for datum in iter_:
        assert datum.properties["this"] == "this"
        assert datum.properties["that"] == "that"

    iter__ = collection.iterator(return_properties=This)
    for datum in iter__:
        assert datum.properties["this"] == "this"
        assert "that" not in datum.properties

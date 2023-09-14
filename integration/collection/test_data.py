import datetime
from typing import Dict, List, TypedDict

import pytest as pytest
import uuid

from weaviate.collection import Collection
from weaviate.collection.classes.config import (
    ConfigFactory,
    Property,
    DataType,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    VectorizerFactory,
)
from weaviate.collection.classes.data import (
    DataObject,
    Error,
)
from weaviate.collection.classes.internal import ReferenceFactory
from weaviate.collection.classes.tenants import Tenant
from weaviate.collection.collection import CollectionObject
from weaviate.collection.data import _DataCollection

from .conftest import CollectionObjectFactory

BEACON_START = "weaviate://localhost"

UUID1 = uuid.uuid4()
UUID2 = uuid.uuid4()
UUID3 = uuid.uuid4()

DATE1 = datetime.datetime.strptime("2012-02-09", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
DATE2 = datetime.datetime.strptime("2013-02-10", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
DATE3 = datetime.datetime.strptime("2019-06-10", "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)


def test_data_with_data_model_with_dict_generic(collection_basic: Collection):
    name = "TestDataWithDictGeneric"

    class Right(TypedDict):
        name: str

    col = collection_basic.get(name)
    assert isinstance(col, CollectionObject)
    data = col.data.with_data_model(Right)
    assert isinstance(data, _DataCollection)


@pytest.mark.parametrize("which_generic", ["typed_dict", "dict", "none"], ids=[0, 1, 2])
def test_insert(collection_basic: Collection, which_generic: str, request_id: str):
    name = f"TestInsert{request_id}"

    create_args = {
        "name": name,
        "properties": [Property(name="Name", data_type=DataType.TEXT)],
        "vectorizer_config": VectorizerFactory.none(),
    }

    class TestInsert(TypedDict):
        name: str

    insert_data = {"name": "some name"}
    if which_generic == "typed_dict":
        collection_basic.create(**create_args)
        collection = collection_basic.get(name, TestInsert)
        uuid = collection.data.insert(properties=TestInsert(**insert_data))
    elif which_generic == "dict":
        collection_basic.create(**create_args)
        collection = collection_basic.get(name, Dict[str, str])
        uuid = collection.data.insert(properties=insert_data)
    else:
        collection = collection_basic.create(**create_args)
        uuid = collection.data.insert(properties=insert_data)
    name = collection.data.get_by_id(uuid).properties["name"]
    assert name == insert_data["name"]


def test_insert_many(collection_object_factory: CollectionObjectFactory):
    name = "TestInsertMany"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    ret = collection.data.insert_many(
        [
            DataObject(properties={"name": "some name"}, vector=[1, 2, 3]),
            DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
        ]
    )
    obj1 = collection.data.get_by_id(ret.uuids[0])
    obj2 = collection.data.get_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"


def test_insert_many_with_typed_dict(collection_object_factory: CollectionObjectFactory):
    name = "TestInsertManyWithTypedDict"

    class TestInsertManyWithTypedDict(TypedDict):
        name: str

    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        data_model=TestInsertManyWithTypedDict,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    ret = collection.data.insert_many(
        [
            DataObject(properties=TestInsertManyWithTypedDict(name="some name"), vector=[1, 2, 3]),
            DataObject(
                properties=TestInsertManyWithTypedDict(name="some other name"), uuid=uuid.uuid4()
            ),
        ]
    )
    obj1 = collection.data.get_by_id(ret.uuids[0])
    obj2 = collection.data.get_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"


def test_insert_many_with_refs(collection_object_factory: CollectionObjectFactory):
    name_target = "RefClassBatchTarget"

    ref_collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name_target,
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid_to1 = ref_collection.data.insert(properties={})
    uuid_to2 = ref_collection.data.insert(properties={})

    name = "TestInsertManyRefs"

    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref_single", target_collection=name_target),
            ReferencePropertyMultiTarget(name="ref_many", target_collections=[name_target, name]),
        ],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid_from = collection.data.insert(properties={"name": "first"})

    ret = collection.data.insert_many(
        [
            DataObject(
                properties={
                    "name": "some name",
                    "ref_single": ReferenceFactory.to(uuids=[uuid_to1, uuid_to2]),
                    "ref_many": ReferenceFactory.to_multi_target(
                        uuids=uuid_from, target_collection=name
                    ),
                },
                vector=[1, 2, 3],
            ),
            DataObject(
                properties={
                    "name": "some other name",
                    "ref_single": ReferenceFactory.to(uuids=uuid_to2),
                    "ref_many": ReferenceFactory.to_multi_target(
                        uuids=uuid_to1, target_collection=name_target
                    ),
                },
                uuid=uuid.uuid4(),
            ),
        ]
    )
    obj1 = collection.data.get_by_id(ret.uuids[0])
    assert obj1.properties["name"] == "some name"
    assert obj1.properties["ref_single"][0]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to1}"
    assert obj1.properties["ref_single"][1]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to2}"
    assert obj1.properties["ref_many"][0]["beacon"] == BEACON_START + f"/{name}/{uuid_from}"

    obj1 = collection.data.get_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some other name"
    assert obj1.properties["ref_single"][0]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to2}"
    assert obj1.properties["ref_many"][0]["beacon"] == BEACON_START + f"/{name_target}/{uuid_to1}"


def test_insert_many_error(collection_object_factory: CollectionObjectFactory):
    name = "TestInsertManyWitHError"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    ret = collection.data.insert_many(
        [
            DataObject(properties={"wrong_name": "some name"}, vector=[1, 2, 3]),
            DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
            DataObject(properties={"other_thing": "is_wrong"}, vector=[1, 2, 3]),
        ]
    )
    assert ret.has_errors

    obj = collection.data.get_by_id(ret.uuids[1])
    assert obj.properties["name"] == "some other name"

    assert len(ret.errors) == 2
    assert 0 in ret.errors and 2 in ret.errors

    assert isinstance(ret.all_responses[0], Error) and isinstance(ret.all_responses[2], Error)
    assert isinstance(ret.all_responses[1], uuid.UUID)


def test_insert_many_with_tenant(collection_object_factory: CollectionObjectFactory):
    name = "TestInsertManyWithTenant"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )

    collection.tenants.add([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    ret = tenant1.data.insert_many(
        [
            DataObject(properties={"name": "some name"}, vector=[1, 2, 3]),
            DataObject(properties={"name": "some other name"}, uuid=uuid.uuid4()),
        ]
    )
    assert not ret.has_errors
    obj1 = tenant1.data.get_by_id(ret.uuids[0])
    obj2 = tenant1.data.get_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"
    assert tenant2.data.get_by_id(ret.uuids[0]) is None
    assert tenant2.data.get_by_id(ret.uuids[1]) is None


def test_replace(collection_object_factory: CollectionObjectFactory):
    name = "TestReplace"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.replace(properties={"name": "other name"}, uuid=uuid)
    assert collection.data.get_by_id(uuid).properties["name"] == "other name"


def test_replace_overwrites_vector(collection_object_factory: CollectionObjectFactory):
    name = "TestReplaceOverwritesVector"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"}, vector=[1, 2, 3])
    obj = collection.data.get_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "some name"
    assert obj.metadata.vector == [1, 2, 3]

    collection.data.replace(properties={"name": "other name"}, uuid=uuid)
    obj = collection.data.get_by_id(uuid, include_vector=True)
    assert obj.properties["name"] == "other name"
    assert obj.metadata.vector is None


def test_replace_with_tenant(collection_object_factory: CollectionObjectFactory):
    name = "TestReplaceWithTenant"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )

    collection.tenants.add([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(properties={"name": "some name"})
    tenant1.data.replace(properties={"name": "other name"}, uuid=uuid)
    assert tenant1.data.get_by_id(uuid).properties["name"] == "other name"
    assert tenant2.data.get_by_id(uuid) is None


def test_update(collection_object_factory: CollectionObjectFactory):
    name = "TestUpdate"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid = collection.data.insert(properties={"name": "some name"})
    collection.data.update(properties={"name": "other name"}, uuid=uuid)
    assert collection.data.get_by_id(uuid).properties["name"] == "other name"


def test_update_with_tenant(collection_object_factory: CollectionObjectFactory):
    name = "TestUpdateWithTenant"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=VectorizerFactory.none(),
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )

    collection.tenants.add([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(properties={"name": "some name"})
    tenant1.data.update(properties={"name": "other name"}, uuid=uuid)
    assert tenant1.data.get_by_id(uuid).properties["name"] == "other name"
    assert tenant2.data.get_by_id(uuid) is None


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
    ids=[0, 1, 2, 3, 4, 5],
)
def test_types(
    collection_object_factory: CollectionObjectFactory, data_type: DataType, value, request_id: str
):
    name = "name"
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=f"Something{request_id}",
        properties=[Property(name=name, data_type=data_type)],
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid_object = collection.data.insert(properties={name: value})

    object_get = collection.data.get_by_id(uuid_object)
    assert object_get.properties[name] == value


def test_reference_add_delete_replace(collection_object_factory: CollectionObjectFactory):
    ref_collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="RefClass2",
        vectorizer_config=VectorizerFactory.none(),
    )
    uuid_to = ref_collection.data.insert(properties={})
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="SomethingElse",
        properties=[ReferenceProperty(name="ref", target_collection="RefClass2")],
        vectorizer_config=VectorizerFactory.none(),
    )

    uuid_from1 = collection.data.insert({}, uuid.uuid4())
    uuid_from2 = collection.data.insert({"ref": ReferenceFactory.to(uuids=uuid_to)}, uuid.uuid4())
    collection.data.reference_add(
        from_uuid=uuid_from1, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_to)
    )
    objects = collection.data.get()
    for obj in objects:
        assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.properties["ref"]])

    collection.data.reference_delete(
        from_uuid=uuid_from1, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_to)
    )
    assert len(collection.data.get_by_id(uuid_from1).properties["ref"]) == 0

    collection.data.reference_add(
        from_uuid=uuid_from2, from_property="ref", ref=ReferenceFactory.to(uuids=uuid_to)
    )
    obj = collection.data.get_by_id(uuid_from2)
    assert len(obj.properties["ref"]) == 2
    assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.properties["ref"]])

    collection.data.reference_replace(
        from_uuid=uuid_from2, from_property="ref", ref=ReferenceFactory.to(uuids=[])
    )
    assert len(collection.data.get_by_id(uuid_from2).properties["ref"]) == 0


def test_get_by_id_with_tenant(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestTenantGet",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )

    collection.tenants.add([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")

    uuid1 = tenant1.data.insert({"name": "some name"})
    obj1 = tenant1.data.get_by_id(uuid1)
    assert obj1.properties["name"] == "some name"

    obj2 = tenant2.data.get_by_id(uuid1)
    assert obj2 is None

    uuid2 = tenant2.data.insert({"name": "some other name"})
    obj3 = tenant2.data.get_by_id(uuid2)
    assert obj3.properties["name"] == "some other name"

    obj4 = tenant1.data.get_by_id(uuid2)
    assert obj4 is None


def test_get_with_limit(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestLimit",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )

    for i in range(10):
        collection.data.insert({"name": str(i)})

    objects = collection.data.get(limit=5)
    assert len(objects) == 5


def test_get_with_tenant(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestTenantGetWithTenant",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
        multi_tenancy_config=ConfigFactory.multi_tenancy(enabled=True),
    )

    collection.tenants.add([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")

    tenant1.data.insert({"name": "some name"})
    objs = tenant1.data.get()
    assert len(objs) == 1
    assert objs[0].properties["name"] == "some name"

    objs = tenant2.data.get()
    assert len(objs) == 0

    tenant2.data.insert({"name": "some other name"})
    objs = tenant2.data.get()
    assert len(objs) == 1
    assert objs[0].properties["name"] == "some other name"


def test_add_property(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestAddProperty",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="name", data_type=DataType.TEXT)],
    )
    uuid1 = collection.data.insert({"name": "first"})
    collection.config.add_property(Property(name="number", data_type=DataType.INT))
    uuid2 = collection.data.insert({"name": "second", "number": 5})
    obj1 = collection.data.get_by_id(uuid1)
    obj2 = collection.data.get_by_id(uuid2)
    assert "name" in obj1.properties
    assert "name" in obj2.properties
    assert "number" in obj2.properties


@pytest.mark.parametrize(
    "hours,minutes,sign", [(0, 0, 1), (1, 20, -1), (2, 0, 1), (3, 40, -1)], ids=[0, 1, 2, 3]
)
def test_insert_date_property(
    collection_object_factory: CollectionObjectFactory,
    hours: int,
    minutes: int,
    sign: int,
    request_id: str,
):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name=f"TestInsertDateProperty{request_id}",
        vectorizer_config=VectorizerFactory.none(),
        properties=[Property(name="date", data_type=DataType.DATE)],
    )

    now = datetime.datetime.now(
        datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))
    )
    uuid = collection.data.insert(properties={"date": now})

    obj = collection.data.get_by_id(uuid)

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


def test_batch_with_arrays(collection_object_factory: CollectionObjectFactory):
    collection = collection_object_factory(
        rest_port=8080,
        grpc_port=50051,
        name="TestBatchArrays",
        vectorizer_config=VectorizerFactory.none(),
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
        obj_out = collection.data.get_by_id(obj_id)

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

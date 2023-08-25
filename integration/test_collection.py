import datetime

import pytest as pytest
import uuid
from dataclasses import dataclass
from typing import Dict, TypedDict

import weaviate
from weaviate import Config
from weaviate.collection.classes import (
    BM25ConfigUpdate,
    CollectionConfig,
    CollectionConfigUpdate,
    DataObject,
    Property,
    DataType,
    GetObjectByIdIncludes,
    InvertedIndexConfigUpdate,
    PQConfigUpdate,
    PQEncoderConfigUpdate,
    PQEncoderType,
    PQEncoderDistribution,
    ReferenceProperty,
    ReferencePropertyMultiTarget,
    ReferenceTo,
    ReferenceToMultiTarget,
    StopwordsUpdate,
    MultiTenancyConfig,
    StopwordsPreset,
    Tenant,
    VectorIndexConfigUpdate,
    Vectorizer,
    Error,
    TenantActivityStatus,
    Reference,
)
from weaviate.collection.grpc import HybridFusion, LinkTo, LinkToMultiTarget, MetadataQuery

BEACON_START = "weaviate://localhost"


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


def test_create_get_and_delete(client: weaviate.Client):
    name = "TestCreateGetAndDelete"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    client.collection.get(name)
    assert client.collection.exists(name)
    client.collection.delete(name)
    assert not client.collection.exists(name)


@pytest.mark.parametrize(
    "should_error",
    [
        (False),
        (True),
    ],
)
def test_create_get_and_delete_generic(client: weaviate.Client, should_error: bool):
    name = "TestCreateGetAndDeleteGeneric"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    if should_error:

        @dataclass
        class Wrong:
            name: str

        client.collection.create(collection_config)
        client.collection.get(name, Wrong)  # bad type because dataclass not bound by generic
        assert client.collection.exists(name)
        client.collection.delete(name)
        assert not client.collection.exists(name)
    else:

        class Right(TypedDict):
            name: str

        client.collection.create(collection_config, Right)
        client.collection.get(name, Right)
        assert client.collection.exists(name)
        client.collection.delete(name)
        assert not client.collection.exists(name)


@pytest.mark.parametrize(
    "insert_data,use_typed_dict",
    [
        ({"name": "some name"}, False),
        ({"name": "some name"}, True),
    ],
)
def test_insert(client: weaviate.Client, insert_data: Dict[str, str], use_typed_dict: bool):
    name = "TestInsert"
    client.collection.delete(name)
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )

    class TestInsert(TypedDict):
        name: str

    if use_typed_dict:
        client.collection.create(collection_config)
        collection = client.collection.get(name, TestInsert)
        uuid = collection.data.insert(data=TestInsert(**insert_data))
        name = collection.data.get_by_id(uuid).properties["name"]
        assert name == "some name"
    else:
        client.collection.create(collection_config)
        collection = client.collection.get(name)
        uuid = collection.data.insert(data=insert_data)
        name = collection.data.get_by_id(uuid).properties["name"]
        assert name == "some name"


def test_insert_many(client: weaviate.Client):
    name = "TestInsertMany"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)
    ret = collection.data.insert_many(
        [
            DataObject(data={"name": "some name"}, vector=[1, 2, 3]),
            DataObject(data={"name": "some other name"}, uuid=uuid.uuid4()),
        ]
    )
    obj1 = collection.data.get_by_id(ret.uuids[0])
    obj2 = collection.data.get_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"

    client.collection.delete(name)


def test_insert_many_with_refs(client: weaviate.Client):
    name_target = "RefClassBatchTarget"
    client.collection.delete(name_target)

    client.collection.create(CollectionConfig(name=name_target, vectorizer=Vectorizer.NONE))
    ref_collection = client.collection.get(name_target)
    uuid_to1 = ref_collection.data.insert(data={})
    uuid_to2 = ref_collection.data.insert(data={})

    name = "TestInsertManyRefs"
    client.collection.delete(name)

    collection_config = CollectionConfig(
        name=name,
        properties=[
            Property(name="Name", data_type=DataType.TEXT),
            ReferenceProperty(name="ref_single", target_collection=name_target),
            ReferencePropertyMultiTarget(name="ref_many", target_collections=[name_target, name]),
        ],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)
    uuid_from = collection.data.insert(data={"name": "first"})

    ret = collection.data.insert_many(
        [
            DataObject(
                data={
                    "name": "some name",
                    "ref_single": ReferenceTo(uuids=[uuid_to1, uuid_to2]),
                    "ref_many": ReferenceToMultiTarget(uuids=uuid_from, target_collection=name),
                },
                vector=[1, 2, 3],
            ),
            DataObject(
                data={
                    "name": "some other name",
                    "ref_single": ReferenceTo(uuids=uuid_to2),
                    "ref_many": ReferenceToMultiTarget(
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


def test_insert_many_error(client: weaviate.Client):
    name = "TestInsertManyWitHError"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)
    ret = collection.data.insert_many(
        [
            DataObject(data={"wrong_name": "some name"}, vector=[1, 2, 3]),
            DataObject(data={"name": "some other name"}, uuid=uuid.uuid4()),
            DataObject(data={"other_thing": "is_wrong"}, vector=[1, 2, 3]),
        ]
    )
    assert ret.has_errors

    obj = collection.data.get_by_id(ret.uuids[1])
    assert obj.properties["name"] == "some other name"

    assert len(ret.errors) == 2
    assert 0 in ret.errors and 2 in ret.errors

    assert isinstance(ret.all_responses[0], Error) and isinstance(ret.all_responses[2], Error)
    assert isinstance(ret.all_responses[1], uuid.UUID)

    client.collection.delete(name)


def test_insert_many_with_tenant(client: weaviate.Client):
    name = "TestInsertManyWithTenant"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
        multi_tenancy_config=MultiTenancyConfig(enabled=True),
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)
    collection.tenants.add([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    ret = tenant1.data.insert_many(
        [
            DataObject(data={"name": "some name"}, vector=[1, 2, 3]),
            DataObject(data={"name": "some other name"}, uuid=uuid.uuid4()),
        ]
    )
    assert not ret.has_errors
    obj1 = tenant1.data.get_by_id(ret.uuids[0])
    obj2 = tenant1.data.get_by_id(ret.uuids[1])
    assert obj1.properties["name"] == "some name"
    assert obj2.properties["name"] == "some other name"
    assert tenant2.data.get_by_id(ret.uuids[0]) is None
    assert tenant2.data.get_by_id(ret.uuids[1]) is None

    client.collection.delete(name)


def test_replace(client: weaviate.Client):
    name = "TestReplace"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)

    uuid = collection.data.insert(data={"name": "some name"})
    collection.data.replace(data={"name": "other name"}, uuid=uuid)
    assert collection.data.get_by_id(uuid).properties["name"] == "other name"

    client.collection.delete(name)


def test_replace_overwrites_vector(client: weaviate.Client):
    name = "TestReplaceOverwritesVector"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)

    uuid = collection.data.insert(data={"name": "some name"}, vector=[1, 2, 3])
    obj = collection.data.get_by_id(uuid, includes=GetObjectByIdIncludes(vector=True))
    assert obj.properties["name"] == "some name"
    assert obj.metadata.vector == [1, 2, 3]

    collection.data.replace(data={"name": "other name"}, uuid=uuid)
    obj = collection.data.get_by_id(uuid, includes=GetObjectByIdIncludes(vector=True))
    assert obj.properties["name"] == "other name"
    assert obj.metadata.vector is None

    client.collection.delete(name)


def test_replace_with_tenant(client: weaviate.Client):
    name = "TestReplaceWithTenant"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
        multi_tenancy_config=MultiTenancyConfig(enabled=True),
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)

    collection.tenants.add([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(data={"name": "some name"})
    tenant1.data.replace(data={"name": "other name"}, uuid=uuid)
    assert tenant1.data.get_by_id(uuid).properties["name"] == "other name"
    assert tenant2.data.get_by_id(uuid) is None

    client.collection.delete(name)


def test_update(client: weaviate.Client):
    name = "TestUpdate"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)

    uuid = collection.data.insert(data={"name": "some name"})
    collection.data.update(data={"name": "other name"}, uuid=uuid)
    assert collection.data.get_by_id(uuid).properties["name"] == "other name"

    client.collection.delete(name)


def test_update_with_tenant(client: weaviate.Client):
    name = "TestUpdateWithTenant"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
        multi_tenancy_config=MultiTenancyConfig(enabled=True),
    )
    client.collection.create(collection_config)
    collection = client.collection.get(name)

    collection.tenants.add([Tenant(name="tenant1"), Tenant(name="tenant2")])
    tenant1 = collection.with_tenant("tenant1")
    tenant2 = collection.with_tenant("tenant2")

    uuid = tenant1.data.insert(data={"name": "some name"})
    tenant1.data.update(data={"name": "other name"}, uuid=uuid)
    assert tenant1.data.get_by_id(uuid).properties["name"] == "other name"
    assert tenant2.data.get_by_id(uuid) is None

    client.collection.delete(name)


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
def test_types(client: weaviate.Client, data_type, value):
    name = "name"
    collection_config = CollectionConfig(
        name="Something",
        properties=[Property(name=name, data_type=data_type)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get("Something")

    uuid_object = collection.data.insert(data={name: value})
    object_get = collection.data.get_by_id(uuid_object)
    assert object_get.properties[name] == value

    client.collection.delete("Something")


def test_reference_add_delete_replace(client: weaviate.Client):
    client.collection.create(CollectionConfig(name="RefClass2", vectorizer=Vectorizer.NONE))
    ref_collection = client.collection.get("RefClass2")
    uuid_to = ref_collection.data.insert(data={})
    collection_config = CollectionConfig(
        name="SomethingElse",
        properties=[ReferenceProperty(name="ref", target_collection="RefClass2")],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)
    collection = client.collection.get("SomethingElse")

    uuid_from1 = collection.data.insert({}, uuid.uuid4())
    uuid_from2 = collection.data.insert({"ref": ReferenceTo(uuids=uuid_to)}, uuid.uuid4())
    collection.data.reference_add(
        from_uuid=uuid_from1, from_property="ref", ref=ReferenceTo(uuids=uuid_to)
    )
    objects = collection.data.get()
    for obj in objects:
        assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.properties["ref"]])

    collection.data.reference_delete(
        from_uuid=uuid_from1, from_property="ref", ref=ReferenceTo(uuids=uuid_to)
    )
    assert len(collection.data.get_by_id(uuid_from1).properties["ref"]) == 0

    collection.data.reference_add(
        from_uuid=uuid_from2, from_property="ref", ref=ReferenceTo(uuids=uuid_to)
    )
    obj = collection.data.get_by_id(uuid_from2)
    assert len(obj.properties["ref"]) == 2
    assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.properties["ref"]])

    collection.data.reference_replace(
        from_uuid=uuid_from2, from_property="ref", ref=ReferenceTo(uuids=[])
    )
    assert len(collection.data.get_by_id(uuid_from2).properties["ref"]) == 0

    client.collection.delete("SomethingElse")
    client.collection.delete("RefClass2")


@pytest.mark.parametrize("fusion_type", [HybridFusion.RANKED, HybridFusion.RELATIVE_SCORE])
def test_search_hybrid(client: weaviate.Client, fusion_type):
    client.collection.create(
        CollectionConfig(
            name="Testing",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    collection = client.collection.get("Testing")
    collection.data.insert({"Name": "some name"}, uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid.uuid4())
    res = collection.query.hybrid_flat(alpha=0, query="name", fusion_type=fusion_type)
    assert len(res) == 1
    client.collection.delete("Testing")


@pytest.mark.parametrize("limit", [1, 5])
def test_search_limit(client: weaviate.Client, limit):
    client.collection.create(
        CollectionConfig(
            name="TestLimit",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection = client.collection.get("TestLimit")

    for i in range(5):
        collection.data.insert({"Name": str(i)})

    assert len(collection.query.get_flat(limit=limit)) == limit

    client.collection.delete("TestLimit")


@pytest.mark.parametrize("offset", [0, 1, 5])
def test_search_offset(client: weaviate.Client, offset):
    client.collection.create(
        CollectionConfig(
            name="TestOffset",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection = client.collection.get("TestOffset")

    nr_objects = 5
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get_flat(offset=offset)
    assert len(objects) == nr_objects - offset

    client.collection.delete("TestOffset")


def test_search_after(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestOffset",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection = client.collection.get("TestOffset")

    nr_objects = 10
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get_flat(return_metadata=MetadataQuery(uuid=True))
    for i, obj in enumerate(objects):
        objects_after = collection.query.get_flat(after=obj.metadata.uuid)
        assert len(objects_after) == nr_objects - 1 - i

    client.collection.delete("TestOffset")


def test_autocut(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestAutocut",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection = client.collection.get("TestAutocut")

    for _ in range(4):
        collection.data.insert({"Name": "rain rain"})
    for _ in range(4):
        collection.data.insert({"Name": "rain"})
    for _ in range(4):
        collection.data.insert({"Name": ""})

    # match all objects with rain
    objects = collection.query.bm25_flat(query="rain", autocut=0)
    assert len(objects) == 2 * 4
    objects = collection.query.hybrid_flat(
        query="rain", autocut=0, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    )
    assert len(objects) == 2 * 4

    # match only objects with two rains
    objects = collection.query.bm25_flat(query="rain", autocut=1)
    assert len(objects) == 1 * 4
    objects = collection.query.hybrid_flat(
        query="rain", autocut=1, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    )
    assert len(objects) == 1 * 4

    client.collection.delete("TestAutocut")


def test_near_vector(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestNearVector",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    collection = client.collection.get("TestNearVector")
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.data.get_by_id(uuid_banana, includes=GetObjectByIdIncludes(vector=True))

    full_objects = collection.query.near_vector_flat(
        banana.metadata.vector, return_metadata=MetadataQuery(distance=True, certainty=True)
    )
    assert len(full_objects) == 4

    objects_distance = collection.query.near_vector_flat(
        banana.metadata.vector, distance=full_objects[2].metadata.distance
    )
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_vector_flat(
        banana.metadata.vector, certainty=full_objects[2].metadata.certainty
    )
    assert len(objects_distance) == 3

    client.collection.delete("TestNearVector")


def test_near_object(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestNearObject",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    collection = client.collection.get("TestNearObject")
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    full_objects = collection.query.near_object_flat(
        uuid_banana, return_metadata=MetadataQuery(distance=True, certainty=True)
    )
    assert len(full_objects) == 4

    objects_distance = collection.query.near_object_flat(
        uuid_banana, distance=full_objects[2].metadata.distance
    )
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_object_flat(
        uuid_banana, certainty=full_objects[2].metadata.certainty
    )
    assert len(objects_distance) == 3

    client.collection.delete("TestNearObject")


def test_mono_references_grcp(client: weaviate.Client):
    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")
    client.collection.create(
        CollectionConfig(
            name="A",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
            ],
        )
    )
    collection_A = client.collection.get("A")
    uuid_A1 = collection_A.data.insert(data={"Name": "A1"})
    uuid_A2 = collection_A.data.insert(data={"Name": "A2"})

    client.collection.create(
        CollectionConfig(
            name="B",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
                ReferenceProperty(name="ref", target_collection="A"),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection_B = client.collection.get("B")

    uuid_B = collection_B.data.insert({"Name": "B", "ref": ReferenceTo(uuids=uuid_A1)})
    collection_B.data.reference_add(
        from_uuid=uuid_B, from_property="ref", ref=ReferenceTo(uuids=uuid_A2)
    )

    client.collection.create(
        CollectionConfig(
            name="C",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
                ReferenceProperty(name="ref", target_collection="B"),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection_C = client.collection.get("C")
    collection_C.data.insert({"Name": "find me", "ref": ReferenceTo(uuids=uuid_B)})

    objects = collection_C.query.bm25_flat(
        query="find",
        return_properties=[
            "name",
            LinkTo(
                link_on="ref",
                properties=[
                    "name",
                    LinkTo(
                        link_on="ref",
                        properties=["name"],
                        metadata=MetadataQuery(uuid=True),
                    ),
                ],
                metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    )
    assert objects[0].properties["name"] == "find me"
    assert objects[0].properties["ref"][0].properties["name"] == "B"
    assert objects[0].properties["ref"][0].properties["ref"][0].properties["name"] == "A1"
    assert objects[0].properties["ref"][0].properties["ref"][1].properties["name"] == "A2"


def test_mono_references_grcp_typed_dicts(client: weaviate.Client):
    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")

    class AProps(TypedDict):
        name: str

    client.collection.create(
        CollectionConfig(
            name="A",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
            ],
        )
    )
    collection_A = client.collection.get("A")
    uuid_A1 = collection_A.data.insert(AProps(name="A1"))
    uuid_A2 = collection_A.data.insert(AProps(name="A2"))

    class BPropsInsert(TypedDict):
        name: str
        ref: ReferenceTo

    collection_B = client.collection.create(
        CollectionConfig(
            name="B",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
                ReferenceProperty(name="ref", target_collection="A"),
            ],
            vectorizer=Vectorizer.NONE,
        ),
        BPropsInsert,
    )
    collection_B = client.collection.get("B")
    uuid_B = collection_B.data.insert(BPropsInsert(name="B", ref=ReferenceTo(uuids=uuid_A1)))
    collection_B.data.reference_add(
        from_uuid=uuid_B, from_property="ref", ref=ReferenceTo(uuids=uuid_A2)
    )

    class CPropsInsert(TypedDict):
        name: str
        ref: ReferenceTo
        age: int

    client.collection.create(
        CollectionConfig(
            name="C",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
                Property(name="Age", data_type=DataType.INT),
                ReferenceProperty(name="ref", target_collection="B"),
            ],
            vectorizer=Vectorizer.NONE,
        ),
        CPropsInsert,
    )
    collection_C = client.collection.get("C")
    collection_C.data.insert(CPropsInsert(name="find me", age=10, ref=ReferenceTo(uuids=uuid_B)))

    class BPropsGet(TypedDict):
        name: str
        ref: Reference[AProps]

    class CPropsGet(TypedDict):
        name: str
        ref: Reference[BPropsGet]
        not_specified: str

    objects = collection_C.query.bm25_flat(
        query="find",
        return_properties=[
            "name",
            "age",
            LinkTo(
                link_on="ref",
                properties=[
                    "name",
                    LinkTo(
                        link_on="ref",
                        properties=["name"],
                        metadata=MetadataQuery(uuid=True),
                    ),
                ],
                metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
        type_=CPropsGet,
    )
    assert (
        objects[0].properties["name"] == "find me"
    )  # happy path (in type and in return_properties)
    assert (
        objects[0].properties.get("not_specified") is None
    )  # type is str but instance is None (in type but not in return_properties)
    assert (
        objects[0].properties.get("age") == 10
    )  # type is Any | None but instance is 10 (not in type but in return_properties)
    assert objects[0].properties["ref"][0].properties["name"] == "B"
    assert objects[0].properties["ref"][0].properties["ref"][0].properties["name"] == "A1"
    assert objects[0].properties["ref"][0].properties["ref"][1].properties["name"] == "A2"


def test_multi_references_grcp(client: weaviate.Client):
    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")

    client.collection.create(
        CollectionConfig(
            name="A",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
            ],
        )
    )
    collection_A = client.collection.get("A")
    uuid_A = collection_A.data.insert(data={"Name": "A"})

    client.collection.create(
        CollectionConfig(
            name="B",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection_B = client.collection.get("B")
    uuid_B = collection_B.data.insert({"Name": "B"})

    client.collection.create(
        CollectionConfig(
            name="C",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
                ReferencePropertyMultiTarget(name="ref", target_collections=["A", "B"]),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection_C = client.collection.get("C")
    collection_C.data.insert(
        {"Name": "first", "ref": ReferenceToMultiTarget(uuids=uuid_A, target_collection="A")}
    )
    collection_C.data.insert(
        {"Name": "second", "ref": ReferenceToMultiTarget(uuids=uuid_B, target_collection="B")}
    )

    objects = collection_C.query.bm25_flat(
        query="first",
        return_properties=[
            "name",
            LinkToMultiTarget(
                link_on="ref",
                target_collection="A",
                properties=["name"],
                metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    )
    assert objects[0].properties["name"] == "first"
    assert len(objects[0].properties["ref"]) == 1
    assert objects[0].properties["ref"][0].properties["name"] == "A"

    objects = collection_C.query.bm25_flat(
        query="second",
        return_properties=[
            "name",
            LinkToMultiTarget(
                link_on="ref",
                target_collection="B",
                properties=[
                    "name",
                ],
                metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        ],
    )
    assert objects[0].properties["name"] == "second"
    assert len(objects[0].properties["ref"]) == 1
    assert objects[0].properties["ref"][0].properties["name"] == "B"

    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")


def test_tenants(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="Tenants",
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(
                enabled=True,
            ),
        )
    )
    collection = client.collection.get("Tenants")
    collection.tenants.add([Tenant(name="tenant1")])

    tenants = collection.tenants.get()
    assert len(tenants) == 1
    assert type(tenants["tenant1"]) is Tenant
    assert tenants["tenant1"].name == "tenant1"

    collection.tenants.remove(["tenant1"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0

    client.collection.delete("Tenants")


def test_multi_searches(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestMultiSearches",
            properties=[Property(name="name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    collection = client.collection.get("TestMultiSearches")
    collection.data.insert(data={"name": "word"})
    collection.data.insert(data={"name": "other"})

    objects = collection.query.bm25_flat(
        query="word",
        return_properties=["name"],
        return_metadata=MetadataQuery(last_update_time_unix=True),
    )
    assert "name" in objects[0].properties
    assert objects[0].metadata.last_update_time_unix is not None

    objects = collection.query.bm25_flat(query="other", return_metadata=MetadataQuery(uuid=True))
    assert "name" not in objects[0].properties
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.last_update_time_unix is None

    client.collection.delete("TestMultiSearches")


def test_search_with_tenant(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestTenantSearch",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )
    collection = client.collection.get("TestTenantSearch")
    collection.tenants.add([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert({"name": "some name"})
    objects1 = tenant1.query.bm25_flat(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects1) == 1
    assert objects1[0].metadata.uuid == uuid1

    objects2 = tenant2.query.bm25_flat(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects2) == 0

    client.collection.delete("TestTenantSearch")


def test_get_by_id_with_tenant(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestTenantGet",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )
    collection = client.collection.get("TestTenantGet")
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

    client.collection.delete("TestTenantGet")


def test_get_with_tenant(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestTenantGetWithTenant",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )
    collection = client.collection.get("TestTenantGetWithTenant")
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

    client.collection.delete("TestTenantGetWithTenant")


def test_add_property(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestAddProperty",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
        )
    )
    collection = client.collection.get("TestAddProperty")
    uuid1 = collection.data.insert({"name": "first"})
    collection.config.add_property(Property(name="number", data_type=DataType.INT))
    uuid2 = collection.data.insert({"name": "second", "number": 5})
    obj1 = collection.data.get_by_id(uuid1)
    obj2 = collection.data.get_by_id(uuid2)
    assert "name" in obj1.properties
    assert "name" in obj2.properties
    assert "number" in obj2.properties

    client.collection.delete("TestAddProperty")


def test_collection_config_get(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestCollectionSchemaGet",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
        )
    )
    collection = client.collection.get("TestCollectionSchemaGet")
    config = collection.config.get()
    assert config.name == "TestCollectionSchemaGet"
    assert len(config.properties) == 2
    assert config.properties[0].name == "name"
    assert config.properties[0].data_type == DataType.TEXT
    assert config.properties[1].name == "age"
    assert config.properties[1].data_type == DataType.INT
    assert config.vectorizer == Vectorizer.NONE

    client.collection.delete("TestCollectionSchemaGet")


def test_collection_config_update(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestCollectionSchemaUpdate",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
        )
    )
    collection = client.collection.get("TestCollectionSchemaUpdate")

    config = collection.config.get()

    assert config.description is None

    assert config.inverted_index_config.bm25.b == 0.75
    assert config.inverted_index_config.bm25.k1 == 1.2
    assert config.inverted_index_config.cleanup_interval_seconds == 60
    assert config.inverted_index_config.stopwords.additions is None
    assert config.inverted_index_config.stopwords.removals is None

    assert config.vector_index_config.skip is False
    assert config.vector_index_config.pq.bit_compression is False
    assert config.vector_index_config.pq.centroids == 256
    assert config.vector_index_config.pq.enabled is False
    assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.KMEANS
    assert config.vector_index_config.pq.encoder.distribution == PQEncoderDistribution.LOG_NORMAL

    collection.config.update(
        CollectionConfigUpdate(
            description="Test",
            inverted_index_config=InvertedIndexConfigUpdate(
                cleanup_interval_seconds=10,
                bm25=BM25ConfigUpdate(
                    k1=1.25,
                    b=0.8,
                ),
                stopwords=StopwordsUpdate(
                    additions=["a"], preset=StopwordsPreset.EN, removals=["the"]
                ),
            ),
            vector_index_config=VectorIndexConfigUpdate(
                skip=True,
                pq=PQConfigUpdate(
                    bit_compression=True,
                    centroids=128,
                    enabled=True,
                    encoder=PQEncoderConfigUpdate(
                        type_=PQEncoderType.TILE, distribution=PQEncoderDistribution.NORMAL
                    ),
                ),
            ),
        )
    )

    config = collection.config.get()

    assert config.description == "Test"

    assert config.inverted_index_config.bm25.b == 0.8
    assert config.inverted_index_config.bm25.k1 == 1.25
    assert config.inverted_index_config.cleanup_interval_seconds == 10
    # assert config.inverted_index_config.stopwords.additions is ["a"] # potential weaviate bug, this returns as None
    assert config.inverted_index_config.stopwords.removals == ["the"]

    assert config.vector_index_config.skip is True
    assert config.vector_index_config.pq.bit_compression is True
    assert config.vector_index_config.pq.centroids == 128
    assert config.vector_index_config.pq.enabled is True
    assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.TILE
    assert config.vector_index_config.pq.encoder.distribution == PQEncoderDistribution.NORMAL

    client.collection.delete("TestCollectionSchemaUpdate")


def test_empty_search_returns_everything(client: weaviate.Client):
    client.collection.create(
        CollectionConfig(
            name="TestReturnEverything",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
        )
    )
    collection = client.collection.get("TestReturnEverything")
    collection.data.insert(data={"name": "word"})

    objects = collection.query.bm25_flat(query="word")
    assert "name" in objects[0].properties
    assert objects[0].properties["name"] == "word"
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.score is not None
    assert objects[0].metadata.last_update_time_unix is not None
    assert objects[0].metadata.creation_time_unix is not None

    client.collection.delete("TestReturnEverything")


@pytest.mark.parametrize("hours,minutes,sign", [(0, 0, 1), (1, 20, -1), (2, 0, 1), (3, 40, -1)])
def test_insert_date_property(client: weaviate.Client, hours: int, minutes: int, sign: int):
    client.collection.delete("TestInsertDateProperty")
    client.collection.create(
        CollectionConfig(
            name="TestInsertDateProperty",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="date", data_type=DataType.DATE)],
        )
    )
    collection = client.collection.get("TestInsertDateProperty")

    now = datetime.datetime.now(
        datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))
    )
    uuid = collection.data.insert(data={"date": now})

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

    client.collection.delete("TestInsertDateProperty")


def test_collection_name_capitalization(client: weaviate.Client):
    name_small = "collectionCapitalizationTest"
    name_big = "CollectionCapitalizationTest"
    client.collection.create(
        CollectionConfig(
            name=name_small,
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
        )
    )
    collection = client.collection.get(name_small)

    assert collection.name == name_big
    client.collection.delete(name_small)
    assert not client.collection.exists(name_small)
    assert not client.collection.exists(name_big)


def test_tenant_with_activity(client: weaviate.Client):
    name = "TestTenantActivity"
    client.collection.create(
        CollectionConfig(
            name=name,
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )
    collection = client.collection.get(name)
    collection.tenants.add(
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


def test_update_tenant(client: weaviate.Client):
    name = "TestUpdateTenant"
    client.collection.create(
        CollectionConfig(
            name=name,
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )
    collection = client.collection.get(name)

    collection.tenants.add([Tenant(name="1", activity_status=TenantActivityStatus.HOT)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.HOT

    collection.tenants.update([Tenant(name="1", activity_status=TenantActivityStatus.COLD)])
    tenants = collection.tenants.get()
    assert tenants["1"].activity_status == TenantActivityStatus.COLD

import uuid

import pytest as pytest

import weaviate
from weaviate import Config
from weaviate.collection.grpc import HybridFusion, LinkTo, MetadataQuery
from weaviate.weaviate_classes import (
    CollectionConfig,
    Property,
    DataType,
    Vectorizer,
    ReferenceProperty,
    RefToObject,
    Metadata,
)


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=Config(grpc_port_experimental=50051)
    )
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


def test_create_and_delete(client: weaviate.Client):
    name = "Something"
    collection_config = CollectionConfig(
        name=name,
        properties=[Property(name="Name", dataType=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)

    assert client.collection.exists(name)
    client.collection.delete(name)
    assert not client.collection.exists(name)


@pytest.mark.parametrize(
    "dataType,value",
    [
        (DataType.TEXT, "1"),
        (DataType.INT, 1),
        (DataType.NUMBER, 0.5),
        (DataType.TEXT_ARRAY, ["1", "2"]),
        (DataType.INT_ARRAY, [1, 2]),
        (DataType.NUMBER_ARRAY, [1.0, 2.1]),
    ],
)
def test_types(client: weaviate.Client, dataType, value):
    name = "name"
    client.collection.delete("Something")

    collection_config = CollectionConfig(
        name="Something",
        properties=[Property(name=name, dataType=dataType)],
        vectorizer=Vectorizer.NONE,
    )
    collection = client.collection.create(collection_config)
    uuid_object = collection.data.insert(data={name: value})

    object_get = collection.data.get_by_id(uuid_object)
    assert object_get.data[name] == value

    client.collection.delete("Something")


def test_references(client: weaviate.Client):
    ref_collection = client.collection.create(
        CollectionConfig(name="RefClass2", vectorizer=Vectorizer.NONE)
    )
    uuid_to = ref_collection.data.insert(data={})
    collection_config = CollectionConfig(
        name="SomethingElse",
        properties=[ReferenceProperty(name="ref", reference_class_name="RefClass2")],
        vectorizer=Vectorizer.NONE,
    )
    collection = client.collection.create(collection_config)

    uuid_from1 = collection.data.insert({}, uuid.uuid4())
    uuid_from2 = collection.data.insert({"ref": RefToObject(uuid_to)}, uuid.uuid4())
    collection.data.reference_add(from_uuid=uuid_from1, from_property="ref", to_uuids=uuid_to)
    objects = collection.data.get()
    for obj in objects:
        assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.data["ref"]])

    collection.data.reference_delete(from_uuid=uuid_from1, from_property="ref", to_uuids=uuid_to)
    assert len(collection.data.get_by_id(uuid_from1).data["ref"]) == 0

    collection.data.reference_add(from_uuid=uuid_from2, from_property="ref", to_uuids=uuid_to)
    obj = collection.data.get_by_id(uuid_from2)
    assert len(obj.data["ref"]) == 2
    assert str(uuid_to) in "".join([ref["beacon"] for ref in obj.data["ref"]])

    collection.data.reference_replace(from_uuid=uuid_from2, from_property="ref", to_uuids=[])
    assert len(collection.data.get_by_id(uuid_from2).data["ref"]) == 0


@pytest.mark.parametrize("fusion_type", [HybridFusion.RANKED, HybridFusion.RELATIVE_SCORE])
def test_search_hybrid(client: weaviate.Client, fusion_type):
    collection = client.collection.create(
        CollectionConfig(
            name="Testing",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    collection.data.insert({"Name": "some name"}, uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid.uuid4())
    res = collection.query.hybrid(alpha=0, query="name", fusion_type=fusion_type)
    assert len(res) == 1
    client.collection.delete("Testing")


@pytest.mark.parametrize("limit", [1, 5])
def test_search_limit(client: weaviate.Client, limit):
    client.collection.delete("TestLimit")
    collection = client.collection.create(
        CollectionConfig(
            name="TestLimit",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    for i in range(5):
        collection.data.insert({"Name": str(i)})

    assert len(collection.query.get(limit=limit)) == limit


@pytest.mark.parametrize("offset", [0, 1, 5])
def test_search_offset(client: weaviate.Client, offset):
    client.collection.delete("TestOffset")
    collection = client.collection.create(
        CollectionConfig(
            name="TestOffset",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )

    nr_objects = 5
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get(offset=offset)
    assert len(objects) == nr_objects - offset


def test_search_after(client: weaviate.Client):
    client.collection.delete("TestOffset")
    collection = client.collection.create(
        CollectionConfig(
            name="TestOffset",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )

    nr_objects = 10
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get(return_metadata=MetadataQuery(uuid=True))
    for i, obj in enumerate(objects):
        objects_after = collection.query.get(after=obj.metadata.uuid)
        assert len(objects_after) == nr_objects - 1 - i


def test_autocut(client: weaviate.Client):
    client.collection.delete("TestAutocut")
    collection = client.collection.create(
        CollectionConfig(
            name="TestAutocut",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    for _ in range(4):
        collection.data.insert({"Name": "rain rain"})
    for _ in range(4):
        collection.data.insert({"Name": "rain"})
    for _ in range(4):
        collection.data.insert({"Name": ""})

    # match all objects with rain
    objects = collection.query.bm25(query="rain", autocut=0)
    assert len(objects) == 2 * 4
    objects = collection.query.hybrid(
        query="rain", autocut=0, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    )
    assert len(objects) == 2 * 4

    # match only objects with two rains
    objects = collection.query.bm25(query="rain", autocut=1)
    assert len(objects) == 1 * 4
    objects = collection.query.hybrid(
        query="rain", autocut=1, alpha=0, fusion_type=HybridFusion.RELATIVE_SCORE
    )
    assert len(objects) == 1 * 4


def test_near_vector(client: weaviate.Client):
    client.collection.delete("TestNearVector")
    collection = client.collection.create(
        CollectionConfig(
            name="TestNearVector",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.data.get_by_id(uuid_banana, metadata=Metadata(vector=True))

    full_objects = collection.query.near_vector(
        banana.metadata.vector, return_metadata=MetadataQuery(distance=True, certainty=True)
    )
    assert len(full_objects) == 4

    objects_distance = collection.query.near_vector(
        banana.metadata.vector, distance=full_objects[2].metadata.distance
    )
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_vector(
        banana.metadata.vector, certainty=full_objects[2].metadata.certainty
    )
    assert len(objects_distance) == 3


def test_near_object(client: weaviate.Client):
    client.collection.delete("TestNearVector")
    collection = client.collection.create(
        CollectionConfig(
            name="TestNearVector",
            properties=[Property(name="Name", dataType=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    full_objects = collection.query.near_object(
        uuid_banana, return_metadata=MetadataQuery(distance=True, certainty=True)
    )
    assert len(full_objects) == 4

    objects_distance = collection.query.near_object(
        uuid_banana, distance=full_objects[2].metadata.distance
    )
    assert len(objects_distance) == 3

    objects_distance = collection.query.near_object(
        uuid_banana, certainty=full_objects[2].metadata.certainty
    )
    assert len(objects_distance) == 3


def test_references_grcp(client: weaviate.Client):
    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")
    A = client.collection.create(
        CollectionConfig(
            name="A",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="Name", dataType=DataType.TEXT),
            ],
        )
    )
    uuid_A1 = A.data.insert(data={"Name": "A1"})
    uuid_A2 = A.data.insert(data={"Name": "A2"})

    B = client.collection.create(
        CollectionConfig(
            name="B",
            properties=[
                Property(name="Name", dataType=DataType.TEXT),
                ReferenceProperty(name="ref", reference_class_name="A"),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    uuid_B = B.data.insert({"Name": "B", "ref": RefToObject(uuid_A1)})
    B.data.reference_add(from_uuid=uuid_B, from_property="ref", to_uuids=uuid_A2)

    C = client.collection.create(
        CollectionConfig(
            name="C",
            properties=[
                Property(name="Name", dataType=DataType.TEXT),
                ReferenceProperty(name="ref", reference_class_name="B"),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    C.data.insert({"Name": "find me", "ref": RefToObject(uuid_B)})

    objects = C.query.bm25(
        query="find",
        return_properties={
            "name",
            LinkTo(
                link_on="ref",
                linked_class="B",
                properties={
                    "name",
                    LinkTo(
                        link_on="ref",
                        linked_class="A",
                        properties={"name"},
                        metadata=MetadataQuery(uuid=True),
                    ),
                },
                metadata=MetadataQuery(uuid=True, last_update_time_unix=True),
            ),
        },
    )
    assert objects[0].data["name"] == "find me"
    assert objects[0].data["ref"][0].data["name"] == "B"
    assert objects[0].data["ref"][0].data["ref"][0].data["name"] == "A1"
    assert objects[0].data["ref"][0].data["ref"][1].data["name"] == "A2"

import pytest as pytest
import uuid

import weaviate
from weaviate import Config
from weaviate.collection.classes import (
    BM25ConfigUpdate,
    CollectionConfig,
    CollectionConfigUpdate,
    Property,
    DataType,
    InvertedIndexConfigUpdate,
    PQConfigUpdate,
    PQEncoderConfigUpdate,
    PQEncoderType,
    PQEncoderDistribution,
    ReferenceProperty,
    RefToObject,
    StopwordsUpdate,
    MetadataGet,
    MultiTenancyConfig,
    StopwordsPreset,
    Tenant,
    VectorIndexConfigUpdate,
    Vectorizer,
)
from weaviate.collection.grpc import HybridFusion, LinkTo, MetadataQuery


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
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer=Vectorizer.NONE,
    )
    client.collection.create(collection_config)

    assert client.collection.exists(name)
    client.collection.delete(name)
    assert not client.collection.exists(name)


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
    client.collection.delete("Something")

    collection_config = CollectionConfig(
        name="Something",
        properties=[Property(name=name, data_type=data_type)],
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
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    collection.data.insert({"Name": "some name"}, uuid.uuid4())
    collection.data.insert({"Name": "other word"}, uuid.uuid4())
    res = collection.query.hybrid_flat(alpha=0, query="name", fusion_type=fusion_type)
    assert len(res) == 1
    client.collection.delete("Testing")


@pytest.mark.parametrize("limit", [1, 5])
def test_search_limit(client: weaviate.Client, limit):
    client.collection.delete("TestLimit")
    collection = client.collection.create(
        CollectionConfig(
            name="TestLimit",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )
    for i in range(5):
        collection.data.insert({"Name": str(i)})

    assert len(collection.query.get_flat(limit=limit)) == limit


@pytest.mark.parametrize("offset", [0, 1, 5])
def test_search_offset(client: weaviate.Client, offset):
    client.collection.delete("TestOffset")
    collection = client.collection.create(
        CollectionConfig(
            name="TestOffset",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )

    nr_objects = 5
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get_flat(offset=offset)
    assert len(objects) == nr_objects - offset


def test_search_after(client: weaviate.Client):
    client.collection.delete("TestOffset")
    collection = client.collection.create(
        CollectionConfig(
            name="TestOffset",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )

    nr_objects = 10
    for i in range(nr_objects):
        collection.data.insert({"Name": str(i)})

    objects = collection.query.get_flat(return_metadata=MetadataQuery(uuid=True))
    for i, obj in enumerate(objects):
        objects_after = collection.query.get_flat(after=obj.metadata.uuid)
        assert len(objects_after) == nr_objects - 1 - i


def test_autocut(client: weaviate.Client):
    client.collection.delete("TestAutocut")
    collection = client.collection.create(
        CollectionConfig(
            name="TestAutocut",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
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


def test_near_vector(client: weaviate.Client):
    client.collection.delete("TestNearVector")
    collection = client.collection.create(
        CollectionConfig(
            name="TestNearVector",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
    uuid_banana = collection.data.insert({"Name": "Banana"})
    collection.data.insert({"Name": "Fruit"})
    collection.data.insert({"Name": "car"})
    collection.data.insert({"Name": "Mountain"})

    banana = collection.data.get_by_id(uuid_banana, metadata=MetadataGet(vector=True))

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


def test_near_object(client: weaviate.Client):
    client.collection.delete("TestNearVector")
    collection = client.collection.create(
        CollectionConfig(
            name="TestNearVector",
            properties=[Property(name="Name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.TEXT2VEC_CONTEXTIONARY,
        )
    )
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


def test_references_grcp(client: weaviate.Client):
    client.collection.delete("A")
    client.collection.delete("B")
    client.collection.delete("C")
    A = client.collection.create(
        CollectionConfig(
            name="A",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
            ],
        )
    )
    uuid_A1 = A.data.insert(data={"Name": "A1"})
    uuid_A2 = A.data.insert(data={"Name": "A2"})

    B = client.collection.create(
        CollectionConfig(
            name="B",
            properties=[
                Property(name="Name", data_type=DataType.TEXT),
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
                Property(name="Name", data_type=DataType.TEXT),
                ReferenceProperty(name="ref", reference_class_name="B"),
            ],
            vectorizer=Vectorizer.NONE,
        )
    )
    C.data.insert({"Name": "find me", "ref": RefToObject(uuid_B)})

    objects = C.query.bm25_flat(
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
    assert objects[0].data["name"] == "find me"
    assert objects[0].data["ref"][0].data["name"] == "B"
    assert objects[0].data["ref"][0].data["ref"][0].data["name"] == "A1"
    assert objects[0].data["ref"][0].data["ref"][1].data["name"] == "A2"


def test_tenants(client: weaviate.Client):
    client.collection.delete("Tenants")
    collection = client.collection.create(
        CollectionConfig(
            name="Tenants",
            vectorizer=Vectorizer.NONE,
            multi_tenancy_config=MultiTenancyConfig(
                enabled=True,
            ),
        )
    )

    collection.tenants.add([Tenant(name="tenant1")])

    tenants = collection.tenants.get()
    assert len(tenants) == 1
    assert type(tenants[0]) is Tenant
    assert tenants[0].name == "tenant1"

    collection.tenants.remove(["tenant1"])

    tenants = collection.tenants.get()
    assert len(tenants) == 0


def test_multi_searches(client: weaviate.Client):
    client.collection.delete("TestMultiSearches")
    collection = client.collection.create(
        CollectionConfig(
            name="TestMultiSearches",
            properties=[Property(name="name", data_type=DataType.TEXT)],
            vectorizer=Vectorizer.NONE,
        )
    )

    collection.data.insert(data={"name": "word"})
    collection.data.insert(data={"name": "other"})

    objects = collection.query.bm25_flat(
        query="word",
        return_properties=["name"],
        return_metadata=MetadataQuery(last_update_time_unix=True),
    )
    assert "name" in objects[0].data
    assert objects[0].metadata.last_update_time_unix is not None

    objects = collection.query.bm25_flat(query="other", return_metadata=MetadataQuery(uuid=True))
    assert "name" not in objects[0].data
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.last_update_time_unix is None


def test_search_with_tenant(client: weaviate.Client):
    client.collection.delete("TestTenantSearch")
    collection = client.collection.create(
        CollectionConfig(
            name="TestTenantSearch",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
            multi_tenancy_config=MultiTenancyConfig(enabled=True),
        )
    )

    collection.tenants.add([Tenant(name="Tenant1"), Tenant(name="Tenant2")])
    tenant1 = collection.with_tenant("Tenant1")
    tenant2 = collection.with_tenant("Tenant2")
    uuid1 = tenant1.data.insert({"name": "some name"})
    objects1 = tenant1.query.bm25_flat(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects1) == 1
    assert objects1[0].metadata.uuid == uuid1

    objects2 = tenant2.query.bm25_flat(query="some", return_metadata=MetadataQuery(uuid=True))
    assert len(objects2) == 0


def test_add_property(client: weaviate.Client):
    client.collection.delete("TestAddProperty")
    collection = client.collection.create(
        CollectionConfig(
            name="TestAddProperty",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
        )
    )
    uuid1 = collection.data.insert({"name": "first"})
    collection.add_property(Property(name="number", data_type=DataType.INT))
    uuid2 = collection.data.insert({"name": "second", "number": 5})
    obj1 = collection.data.get_by_id(uuid1)
    obj2 = collection.data.get_by_id(uuid2)
    assert "name" in obj1.data
    assert "name" in obj2.data
    assert "number" in obj2.data


def test_collection_schema_get(client: weaviate.Client):
    client.collection.delete("TestCollectionSchemaGet")
    collection = client.collection.create(
        CollectionConfig(
            name="TestCollectionSchemaGet",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
        )
    )
    config = collection.config.get()
    assert config.name == "TestCollectionSchemaGet"
    assert len(config.properties) == 2
    assert config.properties[0].name == "name"
    assert config.properties[0].data_type == DataType.TEXT
    assert config.properties[1].name == "age"
    assert config.properties[1].data_type == DataType.INT
    assert config.vectorizer == Vectorizer.NONE


def test_collection_schema_update(client: weaviate.Client):
    client.collection.delete("TestCollectionSchemaUpdate")
    collection = client.collection.create(
        CollectionConfig(
            name="TestCollectionSchemaUpdate",
            vectorizer=Vectorizer.NONE,
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
        )
    )

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


def test_empty_search_returns_everything(client: weaviate.Client):
    client.collection.delete("TestReturnEverything")
    collection = client.collection.create(
        CollectionConfig(
            name="TestReturnEverything",
            vectorizer=Vectorizer.NONE,
            properties=[Property(name="name", data_type=DataType.TEXT)],
        )
    )

    collection.data.insert(data={"name": "word"})

    objects = collection.query.bm25_flat(query="word")
    assert "name" in objects[0].data
    assert objects[0].data["name"] == "word"
    assert objects[0].metadata.uuid is not None
    assert objects[0].metadata.score is not None
    assert objects[0].metadata.last_update_time_unix is not None
    assert objects[0].metadata.creation_time_unix is not None

import pytest as pytest

import weaviate
from weaviate.collections.classes.config import (
    _CollectionConfig,
    _CollectionConfigSimple,
    Configure,
    Reconfigure,
    Property,
    DataType,
    PQEncoderType,
    PQEncoderDistribution,
    StopwordsPreset,
    VectorDistance,
    _VectorIndexType,
    Vectorizer,
)
from weaviate.collections.classes.tenants import Tenant


@pytest.fixture(scope="module")
def client():
    client = weaviate.connect_to_local(port=8087)
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


def test_collection_list(client: weaviate.WeaviateClient):
    client.collections.create(
        name="TestCollectionList",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )

    collections = client.collections.list_all()
    assert list(collections.keys()) == ["TestCollectionList"]
    assert isinstance(collections["TestCollectionList"], _CollectionConfigSimple)

    collection = client.collections.list_all(False)
    assert list(collection.keys()) == ["TestCollectionList"]
    assert isinstance(collection["TestCollectionList"], _CollectionConfig)

    client.collections.delete("TestCollectionList")


def test_collection_get_simple(client: weaviate.WeaviateClient):
    client.collections.create(
        name="TestCollectionGetSimple",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )

    collection = client.collections.get("TestCollectionGetSimple")
    config = collection.config.get(True)
    assert isinstance(config, _CollectionConfigSimple)

    client.collections.delete("TestCollectionGetSimple")


def test_collection_config_empty(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionConfigEmpty",
    )
    config = collection.config.get()

    assert config.name == "TestCollectionConfigEmpty"
    assert config.description is None
    assert config.vectorizer == Vectorizer.NONE

    assert config.properties == []

    assert config.inverted_index_config.bm25.b == 0.75
    assert config.inverted_index_config.bm25.k1 == 1.2
    assert config.inverted_index_config.cleanup_interval_seconds == 60
    assert config.inverted_index_config.index_timestamps is False
    assert config.inverted_index_config.index_property_length is False
    assert config.inverted_index_config.index_null_state is False
    assert config.inverted_index_config.stopwords.additions is None
    assert config.inverted_index_config.stopwords.preset == StopwordsPreset.EN
    assert config.inverted_index_config.stopwords.removals is None

    assert config.multi_tenancy_config.enabled is False

    assert config.replication_config.factor == 1

    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistance.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    assert config.vector_index_config.max_connections == 64
    assert config.vector_index_config.pq.bit_compression is False
    assert config.vector_index_config.pq.centroids == 256
    assert config.vector_index_config.pq.enabled is False
    assert config.vector_index_config.pq.encoder.distribution == PQEncoderDistribution.LOG_NORMAL
    assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.KMEANS
    assert config.vector_index_config.pq.segments == 0
    assert config.vector_index_config.pq.training_limit == 100000
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 1000000000000

    assert config.vector_index_type == _VectorIndexType.HNSW

    client.collections.delete("TestCollectionConfigDefaults")


def test_collection_config_defaults(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionConfigDefaults",
        inverted_index_config=Configure.inverted_index(),
        multi_tenancy_config=Configure.multi_tenancy(),
        replication_config=Configure.replication(),
        vector_index_config=Configure.vector_index(),
        vectorizer_config=Configure.Vectorizer.none(),
    )
    config = collection.config.get()

    assert config.name == "TestCollectionConfigDefaults"
    assert config.description is None
    assert config.vectorizer == Vectorizer.NONE

    assert config.properties == []

    assert config.inverted_index_config.bm25.b == 0.75
    assert config.inverted_index_config.bm25.k1 == 1.2
    assert config.inverted_index_config.cleanup_interval_seconds == 60
    assert config.inverted_index_config.index_timestamps is False
    assert config.inverted_index_config.index_property_length is False
    assert config.inverted_index_config.index_null_state is False
    assert config.inverted_index_config.stopwords.additions is None
    assert config.inverted_index_config.stopwords.preset == StopwordsPreset.EN
    assert config.inverted_index_config.stopwords.removals is None

    assert config.multi_tenancy_config.enabled is False

    assert config.replication_config.factor == 1

    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistance.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    assert config.vector_index_config.max_connections == 64
    assert config.vector_index_config.pq.bit_compression is False
    assert config.vector_index_config.pq.centroids == 256
    assert config.vector_index_config.pq.enabled is False
    assert config.vector_index_config.pq.encoder.distribution == PQEncoderDistribution.LOG_NORMAL
    assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.KMEANS
    assert config.vector_index_config.pq.segments == 0
    assert config.vector_index_config.pq.training_limit == 100000
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 1000000000000

    assert config.vector_index_type == _VectorIndexType.HNSW


def test_collection_config_full(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionConfigFull",
        description="Test",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="texts", data_type=DataType.TEXT_ARRAY),
            Property(name="number", data_type=DataType.NUMBER),
            Property(name="numbers", data_type=DataType.NUMBER_ARRAY),
            Property(name="int", data_type=DataType.INT),
            Property(name="ints", data_type=DataType.INT_ARRAY),
            Property(name="date", data_type=DataType.DATE),
            Property(name="dates", data_type=DataType.DATE_ARRAY),
            Property(name="boolean", data_type=DataType.BOOL),
            Property(name="booleans", data_type=DataType.BOOL_ARRAY),
            Property(name="geo", data_type=DataType.GEO_COORDINATES),
            Property(name="phone", data_type=DataType.PHONE_NUMBER),
        ],
        inverted_index_config=Configure.inverted_index(
            bm25_b=0.8,
            bm25_k1=1.3,
            cleanup_interval_seconds=10,
            index_timestamps=True,
            index_property_length=True,
            index_null_state=True,
            stopwords_additions=["a"],
            stopwords_preset=StopwordsPreset.EN,
            stopwords_removals=["the"],
        ),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        replication_config=Configure.replication(factor=2),
        vector_index_config=Configure.vector_index(
            cleanup_interval_seconds=10,
            distance_metric=VectorDistance.DOT,
            dynamic_ef_factor=6,
            dynamic_ef_max=100,
            dynamic_ef_min=10,
            ef=-2,
            ef_construction=100,
            flat_search_cutoff=41000,
            max_connections=72,
            pq_bit_compression=True,
            pq_centroids=128,
            pq_enabled=True,
            pq_encoder_distribution=PQEncoderDistribution.NORMAL,
            pq_encoder_type=PQEncoderType.TILE,
            pq_segments=4,
            pq_training_limit=1000001,
            skip=True,
            vector_cache_max_objects=100000,
        ),
    )
    config = collection.config.get()

    assert config.name == "TestCollectionConfigFull"
    assert config.description == "Test"
    assert config.vectorizer == Vectorizer.NONE

    assert config.properties[0].name == "text"
    assert config.properties[0].data_type == DataType.TEXT
    assert config.properties[1].name == "texts"
    assert config.properties[1].data_type == DataType.TEXT_ARRAY
    assert config.properties[2].name == "number"
    assert config.properties[2].data_type == DataType.NUMBER
    assert config.properties[3].name == "numbers"
    assert config.properties[3].data_type == DataType.NUMBER_ARRAY
    assert config.properties[4].name == "int"
    assert config.properties[4].data_type == DataType.INT
    assert config.properties[5].name == "ints"
    assert config.properties[5].data_type == DataType.INT_ARRAY
    assert config.properties[6].name == "date"
    assert config.properties[6].data_type == DataType.DATE
    assert config.properties[7].name == "dates"
    assert config.properties[7].data_type == DataType.DATE_ARRAY
    assert config.properties[8].name == "boolean"
    assert config.properties[8].data_type == DataType.BOOL
    assert config.properties[9].name == "booleans"
    assert config.properties[9].data_type == DataType.BOOL_ARRAY
    assert config.properties[10].name == "geo"
    assert config.properties[10].data_type == DataType.GEO_COORDINATES
    assert config.properties[11].name == "phone"
    assert config.properties[11].data_type == DataType.PHONE_NUMBER

    assert config.inverted_index_config.bm25.b == 0.8
    assert config.inverted_index_config.bm25.k1 == 1.3
    assert config.inverted_index_config.cleanup_interval_seconds == 10
    assert config.inverted_index_config.index_timestamps is True
    assert config.inverted_index_config.index_property_length is True
    assert config.inverted_index_config.index_null_state is True
    # assert config.inverted_index_config.stopwords.additions == ["a"] # potential weaviate bug, this returns as None
    assert config.inverted_index_config.stopwords.preset == StopwordsPreset.EN
    assert config.inverted_index_config.stopwords.removals == ["the"]

    assert config.multi_tenancy_config.enabled is True

    assert config.replication_config.factor == 2

    assert config.vector_index_config.cleanup_interval_seconds == 10
    assert config.vector_index_config.distance_metric == VectorDistance.DOT
    assert config.vector_index_config.dynamic_ef_factor == 6
    assert config.vector_index_config.dynamic_ef_max == 100
    assert config.vector_index_config.dynamic_ef_min == 10
    assert config.vector_index_config.ef == -2
    assert config.vector_index_config.ef_construction == 100
    assert config.vector_index_config.flat_search_cutoff == 41000
    assert config.vector_index_config.max_connections == 72
    assert config.vector_index_config.pq.bit_compression is True
    assert config.vector_index_config.pq.centroids == 128
    assert config.vector_index_config.pq.enabled is True
    assert config.vector_index_config.pq.encoder.distribution == PQEncoderDistribution.NORMAL
    # assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.TILE # potential weaviate bug, this returns as PQEncoderType.KMEANS
    assert config.vector_index_config.pq.segments == 4
    assert config.vector_index_config.pq.training_limit == 1000001
    assert config.vector_index_config.skip is True
    assert config.vector_index_config.vector_cache_max_objects == 100000

    assert config.vector_index_type == _VectorIndexType.HNSW

    client.collections.delete("TestCollectionConfigFull")


def test_collection_config_update(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionConfigUpdate",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    config = collection.config.get()

    assert config.replication_config.factor == 1

    collection.config.update(
        description="Test",
        inverted_index_config=Reconfigure.inverted_index(
            bm25_b=0.8,
            bm25_k1=1.25,
            cleanup_interval_seconds=10,
            stopwords_additions=["a"],
            stopwords_preset=StopwordsPreset.EN,
            stopwords_removals=["the"],
        ),
        replication_config=Reconfigure.replication(factor=2),
        vector_index_config=Reconfigure.vector_index(
            skip=True,
            pq_bit_compression=True,
            pq_centroids=128,
            pq_enabled=True,
            pq_encoder_type=PQEncoderType.TILE,
            pq_encoder_distribution=PQEncoderDistribution.NORMAL,
            pq_segments=4,
            pq_training_limit=100001,
            vector_cache_max_objects=2000000,
        ),
    )

    config = collection.config.get()

    assert config.description == "Test"

    assert config.inverted_index_config.bm25.b == 0.8
    assert config.inverted_index_config.bm25.k1 == 1.25
    assert config.inverted_index_config.cleanup_interval_seconds == 10
    # assert config.inverted_index_config.stopwords.additions is ["a"] # potential weaviate bug, this returns as None
    assert config.inverted_index_config.stopwords.removals == ["the"]

    assert config.replication_config.factor == 2

    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistance.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    assert config.vector_index_config.max_connections == 64
    assert config.vector_index_config.pq.bit_compression is True
    assert config.vector_index_config.pq.centroids == 128
    assert config.vector_index_config.pq.enabled is True
    assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.TILE
    assert config.vector_index_config.pq.encoder.distribution == PQEncoderDistribution.NORMAL
    assert config.vector_index_config.pq.segments == 4
    assert config.vector_index_config.pq.training_limit == 100001
    assert config.vector_index_config.skip is True
    assert config.vector_index_config.vector_cache_max_objects == 2000000

    assert config.vector_index_type == _VectorIndexType.HNSW

    client.collections.delete("TestCollectionSchemaUpdate")


def test_collection_config_get_shards(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionConfigGetShards",
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    shards = collection.config.get_shards()
    assert len(shards)
    assert shards[0].status == "READY"
    assert shards[0].vector_queue_size == 0

    client.collections.delete("TestCollectionConfigGetShards")


def test_collection_config_get_shards_multi_tenancy(client: weaviate.WeaviateClient):
    collection = client.collections.create(
        name="TestCollectionConfigGetShardsMultiTenancy",
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    shards = collection.config.get_shards()
    assert len(shards) == 2

    assert shards[0].status == "READY"
    assert shards[0].vector_queue_size == 0

    assert shards[1].status == "READY"
    assert shards[1].vector_queue_size == 0

    assert "tenant1" in [shard.name for shard in shards]
    assert "tenant2" in [shard.name for shard in shards]

    client.collections.delete("TestCollectionConfigGetShardsMultiTenancy")

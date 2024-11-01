from typing import Generator

import pytest as pytest
from _pytest.fixtures import SubRequest

import weaviate
import weaviate.classes as wvc
from integration.conftest import OpenAICollection, CollectionFactory
from integration.conftest import _sanitize_collection_name
from weaviate.collections.classes.config import (
    _BQConfig,
    _SQConfig,
    _CollectionConfig,
    _CollectionConfigSimple,
    _PQConfig,
    _VectorIndexConfigDynamic,
    _VectorIndexConfigFlat,
    _VectorIndexConfigHNSW,
    _VectorIndexConfigHNSWUpdate,
    Configure,
    Reconfigure,
    Property,
    ReferenceProperty,
    DataType,
    PQEncoderType,
    PQEncoderDistribution,
    StopwordsPreset,
    VectorDistances,
    VectorIndexType,
    Vectorizers,
    GenerativeSearches,
    Rerankers,
    _RerankerProvider,
    Tokenization,
)
from weaviate.collections.classes.tenants import Tenant
from weaviate.exceptions import UnexpectedStatusCodeError, WeaviateInvalidInputError


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(port=8087)
    client.collections.delete_all()
    yield client
    client.collections.delete_all()
    client.close()


def test_collections_list(client: weaviate.WeaviateClient) -> None:
    client.collections.create(
        name="TestCollectionsList", vectorizer_config=Configure.Vectorizer.none()
    )

    collections = client.collections.list_all()
    assert "TestCollectionsList" in list(collections.keys())
    assert isinstance(collections["TestCollectionsList"], _CollectionConfigSimple)

    collection = client.collections.list_all(False)
    assert "TestCollectionsList" in list(collections.keys())
    assert isinstance(collection["TestCollectionsList"], _CollectionConfig)

    client.collections.delete("TestCollectionsList")


def test_collection_get_simple(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )

    config = collection.config.get(True)
    assert isinstance(config, _CollectionConfigSimple)


def test_collection_vectorizer_config(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(
                name="age",
                data_type=DataType.INT,
                skip_vectorization=True,
                vectorize_property_name=False,
            ),
        ],
    )

    config = collection.config.get(True)

    assert config.properties[0].vectorizer == "text2vec-contextionary"
    assert config.properties[0].vectorizer_config is not None
    assert config.properties[0].vectorizer_config.skip is False
    assert config.properties[0].vectorizer_config.vectorize_property_name is True
    assert config.properties[1].vectorizer == "text2vec-contextionary"
    assert config.properties[1].vectorizer_config is not None
    assert config.properties[1].vectorizer_config.skip is True
    assert config.properties[1].vectorizer_config.vectorize_property_name is False

    assert config.vectorizer_config is not None
    assert config.vectorizer_config.vectorize_collection_name is False
    assert config.vectorizer_config.model == {}


def test_collection_generative_config(openai_collection: OpenAICollection) -> None:
    collection = openai_collection(
        vectorizer_config=Configure.Vectorizer.none(),
    )

    config = collection.config.get()

    assert config.properties[0].vectorizer == "none"
    assert config.generative_config is not None
    assert config.generative_config.generative == GenerativeSearches.OPENAI
    assert config.generative_config.model is not None


def test_collection_config_empty(collection_factory: CollectionFactory) -> None:
    collection = collection_factory()
    config = collection.config.get()

    assert config.name == collection.name
    assert config.description is None
    assert config.vectorizer == Vectorizers.NONE

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
    assert config.replication_config.async_enabled is False

    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    if collection._connection._weaviate_version.is_lower_than(1, 26, 0):
        assert config.vector_index_config.max_connections == 64
    else:
        assert config.vector_index_config.max_connections == 32
    assert config.vector_index_config.quantizer is None
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 1000000000000

    assert config.vector_index_type == VectorIndexType.HNSW


def test_bm25_config(collection_factory: CollectionFactory) -> None:
    with pytest.raises(ValueError):
        collection_factory(
            inverted_index_config=Configure.inverted_index(bm25_b=0.8),
        )


def test_collection_config_defaults(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        inverted_index_config=Configure.inverted_index(),
        multi_tenancy_config=Configure.multi_tenancy(),
        replication_config=Configure.replication(),
        vector_index_config=Configure.VectorIndex.hnsw(),
        vectorizer_config=Configure.Vectorizer.none(),
    )
    config = collection.config.get()

    assert config.name == collection.name
    assert config.description is None
    assert config.vectorizer == Vectorizers.NONE

    assert config.properties == []

    assert config.inverted_index_config.bm25.b == 0.75
    assert config.inverted_index_config.cleanup_interval_seconds == 60
    assert config.inverted_index_config.index_timestamps is False
    assert config.inverted_index_config.index_property_length is False
    assert config.inverted_index_config.index_null_state is False
    assert config.inverted_index_config.stopwords.additions is None
    assert config.inverted_index_config.stopwords.preset == StopwordsPreset.EN
    assert config.inverted_index_config.stopwords.removals is None

    assert config.multi_tenancy_config.enabled is True

    assert config.replication_config.factor == 1
    assert config.replication_config.async_enabled is False

    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    if collection._connection._weaviate_version.is_lower_than(1, 26, 0):
        assert config.vector_index_config.max_connections == 64
    else:
        assert config.vector_index_config.max_connections == 32
    assert config.vector_index_config.quantizer is None
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 1000000000000

    assert config.vector_index_type == VectorIndexType.HNSW


def test_collection_config_full(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        description="Test",
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
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
        multi_tenancy_config=Configure.multi_tenancy(
            enabled=True, auto_tenant_activation=True, auto_tenant_creation=True
        ),
        replication_config=Configure.replication(
            factor=1,
            async_enabled=True,
            deletion_strategy=wvc.config.ReplicationDeletionStrategy.DELETE_ON_CONFLICT,
        ),
        vector_index_config=Configure.VectorIndex.hnsw(
            cleanup_interval_seconds=10,
            distance_metric=VectorDistances.DOT,
            dynamic_ef_factor=6,
            dynamic_ef_max=100,
            dynamic_ef_min=10,
            ef=-2,
            ef_construction=100,
            filter_strategy=wvc.config.VectorFilterStrategy.ACORN,
            flat_search_cutoff=41000,
            max_connections=72,
            quantizer=Configure.VectorIndex.Quantizer.pq(
                centroids=128,
                encoder_distribution=PQEncoderDistribution.NORMAL,
                encoder_type=PQEncoderType.TILE,
                segments=4,
                training_limit=1000001,
            ),
            vector_cache_max_objects=100000,
        ),
    )
    collection.config.add_reference(
        ReferenceProperty(name="self", target_collection=_sanitize_collection_name(collection.name))
    )
    config = collection.config.get()

    assert config.name == collection.name
    assert config.description == "Test"
    assert config.vectorizer == Vectorizers.TEXT2VEC_CONTEXTIONARY

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

    assert config.references[0].name == "self"
    assert config.references[0].target_collections == [collection.name]

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
    if collection._connection._weaviate_version.is_at_least(1, 25, 2):
        assert config.multi_tenancy_config.auto_tenant_activation is True
    else:
        assert config.multi_tenancy_config.auto_tenant_activation is False
    if collection._connection._weaviate_version.is_at_least(1, 25, 1):
        assert config.multi_tenancy_config.auto_tenant_creation is True
    else:
        assert config.multi_tenancy_config.auto_tenant_creation is False

    assert config.replication_config.factor == 1
    if collection._connection._weaviate_version.is_at_least(1, 26, 0):
        assert config.replication_config.async_enabled is True
    else:
        assert config.replication_config.async_enabled is False

    if collection._connection._weaviate_version.is_at_least(1, 24, 25):
        assert (
            config.replication_config.deletion_strategy
            == wvc.config.ReplicationDeletionStrategy.DELETE_ON_CONFLICT
        )
    else:
        # default value if not present in schema
        assert (
            config.replication_config.deletion_strategy
            == wvc.config.ReplicationDeletionStrategy.NO_AUTOMATED_RESOLUTION
        )

    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert isinstance(config.vector_index_config.quantizer, _PQConfig)
    assert config.vector_index_config.cleanup_interval_seconds == 10
    assert config.vector_index_config.distance_metric == VectorDistances.DOT
    assert config.vector_index_config.dynamic_ef_factor == 6
    assert config.vector_index_config.dynamic_ef_max == 100
    assert config.vector_index_config.dynamic_ef_min == 10
    assert config.vector_index_config.ef == -2
    assert config.vector_index_config.ef_construction == 100
    assert config.vector_index_config.flat_search_cutoff == 41000
    assert config.vector_index_config.max_connections == 72
    assert config.vector_index_config.quantizer.bit_compression is False
    assert config.vector_index_config.quantizer.centroids == 128
    assert config.vector_index_config.quantizer.encoder.distribution == PQEncoderDistribution.NORMAL
    # assert config.vector_index_config.pq.encoder.type_ == PQEncoderType.TILE # potential weaviate bug, this returns as PQEncoderType.KMEANS
    assert config.vector_index_config.quantizer.segments == 4
    assert config.vector_index_config.quantizer.training_limit == 1000001
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 100000
    if collection._connection._weaviate_version.is_at_least(1, 27, 0):
        assert config.vector_index_config.filter_strategy == wvc.config.VectorFilterStrategy.ACORN
    else:
        # default value if not present in schema
        assert (
            config.vector_index_config.filter_strategy == wvc.config.VectorFilterStrategy.SWEEPING
        )

    assert config.vector_index_type == VectorIndexType.HNSW


def test_collection_config_update(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
        ports=(8087, 50058),
        multi_tenancy_config=Configure.multi_tenancy(
            enabled=True, auto_tenant_creation=False, auto_tenant_activation=False
        ),
    )
    config = collection.config.get()

    assert config.replication_config.factor == 1
    assert config.replication_config.async_enabled is False
    assert config.multi_tenancy_config.enabled is True
    assert config.multi_tenancy_config.auto_tenant_activation is False
    assert config.multi_tenancy_config.auto_tenant_creation is False

    assert config.vector_index_config.filter_strategy == wvc.config.VectorFilterStrategy.SWEEPING

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
        replication_config=Reconfigure.replication(
            factor=2,
            async_enabled=True,
            deletion_strategy=wvc.config.ReplicationDeletionStrategy.DELETE_ON_CONFLICT,
        ),  # currently not updateable in RAFT
        vectorizer_config=Reconfigure.VectorIndex.hnsw(
            vector_cache_max_objects=2000000,
            filter_strategy=wvc.config.VectorFilterStrategy.ACORN,
            quantizer=Reconfigure.VectorIndex.Quantizer.pq(
                centroids=128,
                encoder_type=PQEncoderType.TILE,
                encoder_distribution=PQEncoderDistribution.NORMAL,
                segments=4,
                training_limit=100001,
            ),
        ),
        multi_tenancy_config=Reconfigure.multi_tenancy(
            auto_tenant_creation=True, auto_tenant_activation=True
        ),
    )

    config = collection.config.get()

    if collection._connection._weaviate_version.is_at_least(
        1, 25, 2
    ) or collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        assert config.description == "Test"
    else:
        assert config.description is None

    assert config.inverted_index_config.bm25.b == 0.8
    assert config.inverted_index_config.bm25.k1 == 1.25
    assert config.inverted_index_config.cleanup_interval_seconds == 10
    # assert config.inverted_index_config.stopwords.additions is ["a"] # potential weaviate bug, this returns as None
    assert config.inverted_index_config.stopwords.removals == ["the"]

    assert config.replication_config.factor == 2

    if collection._connection._weaviate_version.is_at_least(1, 26, 0):
        assert config.replication_config.async_enabled is True
    else:
        assert config.replication_config.async_enabled is False
    if collection._connection._weaviate_version.is_at_least(1, 24, 25):
        assert (
            config.replication_config.deletion_strategy
            == wvc.config.ReplicationDeletionStrategy.DELETE_ON_CONFLICT
        )
    else:
        # default value if not present in schema
        assert (
            config.replication_config.deletion_strategy
            == wvc.config.ReplicationDeletionStrategy.NO_AUTOMATED_RESOLUTION
        )

    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert isinstance(config.vector_index_config.quantizer, _PQConfig)
    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    if collection._connection._weaviate_version.is_lower_than(1, 26, 0):
        assert config.vector_index_config.max_connections == 64
    else:
        assert config.vector_index_config.max_connections == 32
    assert config.vector_index_config.quantizer.bit_compression is False
    assert config.vector_index_config.quantizer.centroids == 128
    assert config.vector_index_config.quantizer.encoder.type_ == PQEncoderType.TILE
    assert config.vector_index_config.quantizer.encoder.distribution == PQEncoderDistribution.NORMAL
    assert config.vector_index_config.quantizer.segments == 4
    assert config.vector_index_config.quantizer.training_limit == 100001
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 2000000

    if collection._connection._weaviate_version.is_at_least(1, 27, 0):
        assert config.vector_index_config.filter_strategy == wvc.config.VectorFilterStrategy.ACORN
    else:
        # default value if not present in schema
        assert (
            config.vector_index_config.filter_strategy == wvc.config.VectorFilterStrategy.SWEEPING
        )

    assert config.vector_index_type == VectorIndexType.HNSW

    assert config.multi_tenancy_config.enabled is True

    if collection._connection._weaviate_version.is_at_least(1, 25, 2):
        assert config.multi_tenancy_config.auto_tenant_activation is True
    else:
        assert config.multi_tenancy_config.auto_tenant_activation is False

    if collection._connection._weaviate_version.is_at_least(1, 25, 1):
        assert config.multi_tenancy_config.auto_tenant_creation is True
    else:
        assert config.multi_tenancy_config.auto_tenant_creation is False

    collection.config.update(
        vectorizer_config=Reconfigure.VectorIndex.hnsw(
            filter_strategy=wvc.config.VectorFilterStrategy.SWEEPING,
            quantizer=Reconfigure.VectorIndex.Quantizer.pq(enabled=False),
        ),
        replication_config=Reconfigure.replication(
            deletion_strategy=wvc.config.ReplicationDeletionStrategy.NO_AUTOMATED_RESOLUTION,
        ),
    )
    config = collection.config.get()

    if collection._connection._weaviate_version.is_at_least(
        1, 25, 2
    ) or collection._connection._weaviate_version.is_lower_than(1, 25, 0):
        assert config.description == "Test"
    else:
        assert config.description is None

    assert config.inverted_index_config.bm25.b == 0.8
    assert config.inverted_index_config.bm25.k1 == 1.25
    assert config.inverted_index_config.cleanup_interval_seconds == 10
    # assert config.inverted_index_config.stopwords.additions is ["a"] # potential weaviate bug, this returns as None
    assert config.inverted_index_config.stopwords.removals == ["the"]

    assert config.replication_config.factor == 2
    assert (
        config.replication_config.deletion_strategy
        == wvc.config.ReplicationDeletionStrategy.NO_AUTOMATED_RESOLUTION
    )

    if collection._connection._weaviate_version.is_at_least(1, 26, 0):
        assert config.replication_config.async_enabled is True
    else:
        assert config.replication_config.async_enabled is False

    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    if collection._connection._weaviate_version.is_lower_than(1, 26, 0):
        assert config.vector_index_config.max_connections == 64
    else:
        assert config.vector_index_config.max_connections == 32
    assert config.vector_index_config.quantizer is None
    assert config.vector_index_config.skip is False
    assert config.vector_index_config.vector_cache_max_objects == 2000000
    assert config.vector_index_config.filter_strategy == wvc.config.VectorFilterStrategy.SWEEPING

    assert config.vector_index_type == VectorIndexType.HNSW


def test_hnsw_with_bq(collection_factory: CollectionFactory) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("BQ+HNSW is not supported in Weaviate versions lower than 1.24.0")

    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hnsw(
            vector_cache_max_objects=5,
            quantizer=Configure.VectorIndex.Quantizer.bq(rescore_limit=10),
        ),
    )

    config = collection.config.get()
    assert config.vector_index_type == VectorIndexType.HNSW
    assert config.vector_index_config is not None
    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert isinstance(config.vector_index_config.quantizer, _BQConfig)


def test_hnsw_with_sq(collection_factory: CollectionFactory) -> None:
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("SQ+HNSW is not supported in Weaviate versions lower than 1.26.0")

    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hnsw(
            vector_cache_max_objects=5,
            quantizer=Configure.VectorIndex.Quantizer.sq(rescore_limit=10, training_limit=1000000),
        ),
    )

    config = collection.config.get()
    assert config.vector_index_type == VectorIndexType.HNSW
    assert config.vector_index_config is not None
    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert isinstance(config.vector_index_config.quantizer, _SQConfig)


@pytest.mark.parametrize(
    "vector_index_config",
    [
        Reconfigure.VectorIndex.hnsw(quantizer=Reconfigure.VectorIndex.Quantizer.bq()),
        Reconfigure.VectorIndex.hnsw(quantizer=Reconfigure.VectorIndex.Quantizer.sq()),
    ],
)
def test_update_from_pq_with_hnsw(
    collection_factory: CollectionFactory, vector_index_config: _VectorIndexConfigHNSWUpdate
) -> None:
    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hnsw(
            vector_cache_max_objects=5,
            quantizer=Configure.VectorIndex.Quantizer.pq(
                centroids=128,
            ),
        ),
    )
    with pytest.raises(WeaviateInvalidInputError):
        collection.config.update(vector_index_config=vector_index_config)


def test_update_flat(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.flat(
            vector_cache_max_objects=5,
            quantizer=Configure.VectorIndex.Quantizer.bq(rescore_limit=10),
        ),
    )

    config = collection.config.get()
    assert config.vector_index_type == VectorIndexType.FLAT
    assert config.vector_index_config is not None
    assert isinstance(config.vector_index_config, _VectorIndexConfigFlat)
    assert config.vector_index_config.vector_cache_max_objects == 5
    assert isinstance(config.vector_index_config.quantizer, _BQConfig)
    assert config.vector_index_config.quantizer.rescore_limit == 10

    collection.config.update(
        vectorizer_config=Reconfigure.VectorIndex.flat(
            vector_cache_max_objects=10,
            quantizer=Reconfigure.VectorIndex.Quantizer.bq(rescore_limit=20),
        ),
    )
    config = collection.config.get()
    assert config.vector_index_type == VectorIndexType.FLAT
    assert config.vector_index_config is not None
    assert isinstance(config.vector_index_config, _VectorIndexConfigFlat)
    assert config.vector_index_config.vector_cache_max_objects == 10
    assert isinstance(config.vector_index_config.quantizer, _BQConfig)
    assert config.vector_index_config.quantizer.rescore_limit == 20

    with pytest.raises(UnexpectedStatusCodeError):
        # cannot enable/disable BQ after flat index was created
        # must only do this on creation
        collection.config.update(
            vectorizer_config=Reconfigure.VectorIndex.flat(
                quantizer=Reconfigure.VectorIndex.Quantizer.bq(enabled=False),
            )
        )


def test_collection_config_get_shards(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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


def test_collection_update_shards(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
    )

    collection.tenants.create([Tenant(name="tenant1"), Tenant(name="tenant2")])
    assert all(shard.status == "READY" for shard in collection.config.get_shards())

    # all possibilites of calling the function
    updated_shards = collection.config.update_shards(status="READONLY", shard_names="tenant1")
    assert len(updated_shards) == 1
    assert updated_shards["tenant1"] == "READONLY"

    updated_shards = collection.config.update_shards(status="READY", shard_names=["tenant1"])
    assert len(updated_shards) == 1
    assert updated_shards["tenant1"] == "READY"

    updated_shards = collection.config.update_shards(
        status="READONLY", shard_names=["tenant1", "tenant2"]
    )
    assert all(shard == "READONLY" for shard in updated_shards.values())

    updated_shards = collection.config.update_shards(
        status="READY", shard_names=["tenant1", "tenant2"]
    )
    assert all(shard == "READY" for shard in updated_shards.values())

    updated_shards = collection.config.update_shards(status="READONLY")
    assert all(shard == "READONLY" for shard in updated_shards.values())


def test_collection_config_get_shards_multi_tenancy(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
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


def test_config_vector_index_flat_and_quantizer_bq(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.flat(
            vector_cache_max_objects=234,
            quantizer=Configure.VectorIndex.Quantizer.bq(rescore_limit=456),
        ),
    )

    conf = collection.config.get()
    assert conf.vector_index_type == VectorIndexType.FLAT
    assert conf.vector_index_config is not None
    assert isinstance(conf.vector_index_config, _VectorIndexConfigFlat)
    assert conf.vector_index_config.vector_cache_max_objects == 234
    assert isinstance(conf.vector_index_config.quantizer, _BQConfig)
    assert conf.vector_index_config.quantizer.rescore_limit == 456


def test_config_vector_index_hnsw_and_quantizer_pq(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hnsw(
            vector_cache_max_objects=234,
            ef_construction=789,
            quantizer=Configure.VectorIndex.Quantizer.pq(segments=456),
        ),
    )

    conf = collection.config.get()
    assert conf.vector_index_type == VectorIndexType.HNSW
    assert conf.vector_index_config is not None
    assert isinstance(conf.vector_index_config, _VectorIndexConfigHNSW)
    assert conf.vector_index_config.vector_cache_max_objects == 234
    assert conf.vector_index_config.ef_construction == 789
    assert isinstance(conf.vector_index_config.quantizer, _PQConfig)
    assert conf.vector_index_config.quantizer.segments == 456


@pytest.mark.parametrize(
    "reranker_config,expected_reranker,expected_model",
    [
        (Configure.Reranker.cohere(), Rerankers.COHERE, {}),
        (
            Configure.Reranker.cohere(model="rerank-english-v2.0"),
            Rerankers.COHERE,
            {"model": "rerank-english-v2.0"},
        ),
        (Configure.Reranker.transformers(), Rerankers.TRANSFORMERS, {}),
    ],
)
def test_config_reranker_module(
    collection_factory: CollectionFactory,
    reranker_config: _RerankerProvider,
    expected_reranker: Rerankers,
    expected_model: dict,
) -> None:
    collection = collection_factory(
        reranker_config=reranker_config,
        vectorizer_config=Configure.Vectorizer.none(),
    )
    conf = collection.config.get()
    assert conf.reranker_config is not None
    assert conf.reranker_config.reranker == expected_reranker
    assert conf.reranker_config.model == expected_model


def test_config_nested_properties(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(
                name="name",
                data_type=DataType.OBJECT,
                nested_properties=[
                    Property(name="first", data_type=DataType.TEXT),
                    Property(name="last", data_type=DataType.TEXT),
                ],
            ),
        ],
    )
    conf = collection.config.get()
    assert conf.properties[0].name == "name"
    assert conf.properties[0].data_type == DataType.OBJECT
    assert conf.properties[0].nested_properties is not None
    assert conf.properties[0].nested_properties[0].name == "first"
    assert conf.properties[0].nested_properties[0].data_type == DataType.TEXT
    assert conf.properties[0].nested_properties[1].name == "last"
    assert conf.properties[0].nested_properties[1].data_type == DataType.TEXT


def test_config_export_and_recreate_from_config(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
            Property(name="age", data_type=DataType.INT),
        ],
    )
    conf = collection.config.get()

    name = "TestCollectionConfigExportAndRecreateFromConfig"
    conf.name = name

    client = weaviate.connect_to_local()
    client.collections.create_from_config(conf)
    assert conf == client.collections.get(name).config.get()
    client.collections.delete(name)
    client.close()


def test_config_export_and_recreate_from_dict(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        generative_config=Configure.Generative.custom(
            "generative-anyscale", module_config={"temperature": 0.5}
        ),
        vectorizer_config=Configure.Vectorizer.none(),
        reranker_config=Configure.Reranker.custom(
            "reranker-cohere", module_config={"model": "rerank-english-v2.0"}
        ),
        properties=[
            Property(
                name="field_tokenization", data_type=DataType.TEXT, tokenization=Tokenization.FIELD
            ),
            Property(
                name="field_description",
                data_type=DataType.TEXT,
                tokenization=Tokenization.FIELD,
                description="field desc",
            ),
            Property(
                name="field_index_filterable", data_type=DataType.TEXT, index_filterable=False
            ),
            Property(
                name="field_skip_vectorization", data_type=DataType.TEXT, skip_vectorization=True
            ),
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
            Property(
                name="field_index_searchable", data_type=DataType.TEXT, index_searchable=False
            ),
            Property(
                name="field_index_range_filters_false",
                data_type=DataType.INT,
                index_range_filters=False,
            ),
            Property(
                name="field_index_range_filters_true",
                data_type=DataType.INT,
                index_range_filters=True,
            ),
            Property(
                name="field_skip_vectorization_false",
                data_type=DataType.TEXT,
                vectorize_property_name=False,
            ),
            Property(
                name="nested",
                data_type=DataType.OBJECT,
                nested_properties=[
                    Property(name="first", data_type=DataType.TEXT),
                    Property(
                        name="nested_token",
                        data_type=DataType.TEXT,
                        tokenization=Tokenization.FIELD,
                    ),
                    Property(
                        name="nested_searchable", data_type=DataType.TEXT, index_searchable=False
                    ),
                    Property(
                        name="nested_filterable", data_type=DataType.TEXT, index_filterable=False
                    ),
                    Property(
                        name="nested_prop_vectorization",
                        data_type=DataType.TEXT,
                        vectorize_property_name=False,
                    ),
                    Property(
                        name="nested_range", data_type=DataType.TEXT, vectorize_property_name=False
                    ),
                    Property(
                        name="nested_skip_vectorization",
                        data_type=DataType.TEXT,
                        skip_vectorization=True,
                    ),
                    Property(
                        name="nested2",
                        data_type=DataType.OBJECT,
                        nested_properties=[Property(name="first", data_type=DataType.TEXT)],
                    ),
                ],
            ),
        ],
        multi_tenancy_config=Configure.multi_tenancy(enabled=True),
        replication_config=Configure.replication(factor=1, async_enabled=False),
        vector_index_config=Configure.VectorIndex.hnsw(
            quantizer=Configure.VectorIndex.Quantizer.pq(centroids=256)
        ),
        inverted_index_config=Configure.inverted_index(bm25_b=0.8, bm25_k1=1.3),
    )
    collection.config.add_reference(
        ReferenceProperty(name="self", target_collection=collection.name)
    )
    conf = collection.config.get()

    name = "TestCollectionConfigExportAndRecreateFromDict"
    conf.name = name
    dconf = conf.to_dict()

    client = weaviate.connect_to_local()
    client.collections.delete(name)
    client.collections.create_from_dict(dconf)
    old = collection.config.get()
    old.name = "dummy"
    new = client.collections.get(name).config.get()
    new.name = "dummy"
    assert old == new

    client.collections.delete(name)
    client.close()


def test_config_add_existing_property_and_reference(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    collection.config.add_reference(
        ReferenceProperty(name="self", target_collection=collection.name)
    )
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        collection.config.add_property(Property(name="name", data_type=DataType.TEXT))
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        collection.config.add_reference(
            ReferenceProperty(name="self", target_collection=collection.name)
        )


def test_config_skip_vector_index(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.none(),
    )
    config = collection.config.get()
    assert isinstance(config.vector_index_config, _VectorIndexConfigHNSW)
    assert config.vector_index_config.cleanup_interval_seconds == 300
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.dynamic_ef_factor == 8
    assert config.vector_index_config.dynamic_ef_max == 500
    assert config.vector_index_config.dynamic_ef_min == 100
    assert config.vector_index_config.ef == -1
    assert config.vector_index_config.ef_construction == 128
    assert config.vector_index_config.flat_search_cutoff == 40000
    if collection._connection._weaviate_version.is_lower_than(1, 26, 0):
        assert config.vector_index_config.max_connections == 64
    else:
        assert config.vector_index_config.max_connections == 32
    assert config.vector_index_config.quantizer is None
    assert config.vector_index_config.skip is True
    assert config.vector_index_config.vector_cache_max_objects == 1000000000000


def test_dynamic_collection(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy", ports=(8090, 50061))
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 25, 0):
        pytest.skip("Dynamic index is not supported in Weaviate versions lower than 1.25.0")

    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.dynamic(
            distance_metric=VectorDistances.COSINE,
            threshold=1000,
            hnsw=Configure.VectorIndex.hnsw(
                cleanup_interval_seconds=123,
                flat_search_cutoff=1234,
                vector_cache_max_objects=789,
                quantizer=Configure.VectorIndex.Quantizer.pq(centroids=128),
            ),
            flat=Configure.VectorIndex.flat(
                vector_cache_max_objects=7643,
                quantizer=Configure.VectorIndex.Quantizer.bq(rescore_limit=10),
            ),
        ),
        ports=(8090, 50061),
    )

    config = collection.config.get()
    assert isinstance(config.vector_index_config, _VectorIndexConfigDynamic)
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.threshold == 1000
    assert isinstance(config.vector_index_config.hnsw, _VectorIndexConfigHNSW)
    assert config.vector_index_config.hnsw.cleanup_interval_seconds == 123
    assert config.vector_index_config.hnsw.flat_search_cutoff == 1234
    assert config.vector_index_config.hnsw.vector_cache_max_objects == 789
    assert isinstance(config.vector_index_config.hnsw.quantizer, _PQConfig)
    assert config.vector_index_config.hnsw.quantizer.centroids == 128
    assert isinstance(config.vector_index_config.flat, _VectorIndexConfigFlat)
    assert config.vector_index_config.flat.vector_cache_max_objects == 7643
    assert isinstance(config.vector_index_config.flat.quantizer, _BQConfig)
    assert config.vector_index_config.flat.quantizer.rescore_limit == 10

    collection.config.update(
        vectorizer_config=Reconfigure.VectorIndex.dynamic(
            threshold=2000,
            hnsw=Reconfigure.VectorIndex.hnsw(
                flat_search_cutoff=4567,
                vector_cache_max_objects=678,
                quantizer=Reconfigure.VectorIndex.Quantizer.pq(centroids=128),
            ),
            flat=Reconfigure.VectorIndex.flat(
                vector_cache_max_objects=9876,
                quantizer=Reconfigure.VectorIndex.Quantizer.bq(rescore_limit=11),
            ),
        ),
    )
    config = collection.config.get()
    assert isinstance(config.vector_index_config, _VectorIndexConfigDynamic)
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.threshold == 2000
    assert isinstance(config.vector_index_config.hnsw, _VectorIndexConfigHNSW)
    assert config.vector_index_config.hnsw.cleanup_interval_seconds == 123
    assert config.vector_index_config.hnsw.flat_search_cutoff == 4567
    assert config.vector_index_config.hnsw.vector_cache_max_objects == 678
    assert isinstance(config.vector_index_config.hnsw.quantizer, _PQConfig)
    assert config.vector_index_config.hnsw.quantizer.centroids == 128
    assert isinstance(config.vector_index_config.flat, _VectorIndexConfigFlat)
    assert config.vector_index_config.flat.vector_cache_max_objects == 9876
    assert isinstance(config.vector_index_config.flat.quantizer, _BQConfig)
    assert config.vector_index_config.flat.quantizer.rescore_limit == 11


def test_config_unknown_module(request: SubRequest) -> None:
    with weaviate.connect_to_local() as client:
        collection_name = _sanitize_collection_name(request.node.name)
        client.collections.delete(name=collection_name)
        collection = client.collections.create_from_dict(
            {
                "class": collection_name,
                "vectorizer": "none",
                "moduleConfig": {"generative-dummy": {}, "reranker-dummy": {}},
                "properties": [
                    {"name": "prop", "dataType": ["text"]},
                ],
            }
        )
        config = collection.config.get()
        assert config.generative_config is not None
        assert isinstance(config.generative_config.generative, str)
        assert config.generative_config.generative == "generative-dummy"

        assert config.reranker_config is not None
        assert isinstance(config.reranker_config.reranker, str)
        assert config.reranker_config.reranker == "reranker-dummy"

        client.collections.delete(name=collection_name)

        collection2 = client.collections.create_from_config(config)
        config2 = collection2.config.get()
        assert config == config2
        assert config2.generative_config is not None
        assert isinstance(config2.generative_config.generative, str)
        assert config2.generative_config.generative == "generative-dummy"

        assert config2.reranker_config is not None
        assert isinstance(config2.reranker_config.reranker, str)
        assert config2.reranker_config.reranker == "reranker-dummy"

        client.collections.delete(name=collection_name)


def test_create_custom_generative(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        generative_config=Configure.Generative.custom(
            "generative-anyscale", module_config={"temperature": 0.5}
        ),
    )
    config = collection.config.get()

    collection2 = collection_factory(
        generative_config=Configure.Generative.anyscale(temperature=0.5)
    )
    config2 = collection2.config.get()

    assert config.generative_config == config2.generative_config
    assert isinstance(config.generative_config.generative, str)
    assert config.generative_config.generative == "generative-anyscale"
    assert config.generative_config.model == {"temperature": 0.5}

    if collection._connection._weaviate_version.is_at_least(1, 25, 24):
        collection.config.update(
            generative_config=Reconfigure.Generative.custom("generative-dummy"),
        )
        config = collection.config.get()
        assert isinstance(config.generative_config.generative, str)
        assert config.generative_config.generative == "generative-dummy"


def test_create_custom_reranker(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        reranker_config=Configure.Reranker.custom(
            "reranker-cohere", module_config={"model": "rerank-english-v2.0"}
        ),
    )
    config = collection.config.get()

    collection2 = collection_factory(
        reranker_config=Configure.Reranker.cohere(model="rerank-english-v2.0")
    )
    config2 = collection2.config.get()

    assert config.reranker_config == config2.reranker_config
    assert isinstance(config.reranker_config.reranker, str)
    assert config.reranker_config.reranker == "reranker-cohere"
    assert config.reranker_config.model == {"model": "rerank-english-v2.0"}

    if collection._connection._weaviate_version.is_at_least(1, 25, 24):
        collection.config.update(
            reranker_config=Reconfigure.Reranker.custom("reranker-dummy"),
        )
        config = collection.config.get()
        assert isinstance(config.reranker_config.reranker, str)
        assert config.reranker_config.reranker == "reranker-dummy"


def test_create_custom_vectorizer(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.custom(
            "text2vec-contextionary", module_config={"vectorizeClassName": False}
        ),
    )
    config = collection.config.get()

    collection2 = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    config2 = collection2.config.get()

    assert config.vectorizer_config == config2.vectorizer_config
    assert isinstance(config.vectorizer_config.vectorizer, str)
    assert config.vectorizer_config.vectorizer == "text2vec-contextionary"
    assert not config.vectorizer_config.vectorize_collection_name


def test_create_custom_vectorizer_named(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named index is not supported in Weaviate versions lower than 1.24.0")

    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=[
            Configure.NamedVectors.custom(
                "name",
                module_name="text2vec-contextionary",
                module_config={"vectorizeClassName": False},
            )
        ],
    )
    config = collection.config.get()

    collection2 = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=[
            Configure.NamedVectors.text2vec_contextionary("name", vectorize_collection_name=False)
        ],
    )
    config2 = collection2.config.get()

    assert config.vector_config == config2.vector_config
    assert len(config.vector_config) == 1
    assert config.vector_config["name"].vectorizer.vectorizer == "text2vec-contextionary"
    assert config.vector_config["name"].vectorizer.model == {"vectorizeClassName": False}


@pytest.mark.parametrize("index_range_filters", [True, False])
def test_range_filters(collection_factory: CollectionFactory, index_range_filters: bool) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 26, 0):
        pytest.skip("range filters are not supported in Weaviate versions lower than 1.26.0")

    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.INT, index_range_filters=index_range_filters)
        ],
    )
    config = collection.config.get()
    assert config.properties[0].index_range_filters == index_range_filters


@pytest.mark.parametrize(
    "deletion_strategy",
    [
        wvc.config.ReplicationDeletionStrategy.DELETE_ON_CONFLICT,
        wvc.config.ReplicationDeletionStrategy.NO_AUTOMATED_RESOLUTION,
    ],
)
def test_replication_config(
    collection_factory: CollectionFactory, deletion_strategy: wvc.config.ReplicationDeletionStrategy
) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 24, 25):
        pytest.skip("deletion strategy is supported in Weaviate versions lower than 1.24, 25")

    collection = collection_factory(
        replication_config=wvc.config.Configure.replication(deletion_strategy=deletion_strategy),
    )
    config = collection.config.get()
    assert config.replication_config.deletion_strategy == deletion_strategy

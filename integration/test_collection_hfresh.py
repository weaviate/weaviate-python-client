import pytest
import weaviate
from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    Reconfigure,
    VectorDistances,
    VectorIndexType,
    Vectorizers,
    _MuveraConfig,
    _VectorIndexConfigHFresh,
)


def test_collection_config_hfresh(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 36, 0):
        pytest.skip("Hfresh index is not supported in Weaviate versions lower than 1.36.0")

    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hfresh(
            distance_metric=VectorDistances.COSINE,
            max_posting_size_kb=1024,
            replicas=2,
            search_probe=50,
        )
    )

    config = collection.config.get()

    assert config.vector_index_type == VectorIndexType.HFRESH
    assert isinstance(config.vector_index_config, _VectorIndexConfigHFresh)
    assert config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert config.vector_index_config.max_posting_size_kb == 1024
    assert config.vector_index_config.replicas == 2
    assert config.vector_index_config.search_probe == 50


def test_collection_named_vectors_hfresh(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 36, 0):
        pytest.skip("Hfresh index is not supported in Weaviate versions lower than 1.36.0")

    collection = collection_factory(
        vector_config=[
            Configure.Vectors.self_provided(
                name="title_vec",
                vector_index_config=Configure.VectorIndex.hfresh(
                    distance_metric=VectorDistances.COSINE,
                    max_posting_size_kb=512,
                    replicas=1,
                    search_probe=25,
                ),
            ),
        ],
    )

    config = collection.config.get()

    assert config.vector_config is not None
    assert "title_vec" in config.vector_config

    title_config = config.vector_config["title_vec"]
    assert title_config.vectorizer.vectorizer == Vectorizers.NONE
    assert isinstance(title_config.vector_index_config, _VectorIndexConfigHFresh)
    assert title_config.vector_index_config.distance_metric == VectorDistances.COSINE
    assert title_config.vector_index_config.max_posting_size_kb == 512
    assert title_config.vector_index_config.replicas == 1
    assert title_config.vector_index_config.search_probe == 25


def test_collection_update_hfresh(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 36, 0):
        pytest.skip("Hfresh index is not supported in Weaviate versions lower than 1.36.0")

    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hfresh(
            distance_metric=VectorDistances.COSINE,
            max_posting_size_kb=512,
            replicas=1,
            search_probe=25,
        )
    )

    config = collection.config.get()
    assert isinstance(config.vector_index_config, _VectorIndexConfigHFresh)
    assert config.vector_index_config.max_posting_size_kb == 512
    assert config.vector_index_config.replicas == 1
    assert config.vector_index_config.search_probe == 25

    collection.config.update(vectorizer_config=Reconfigure.VectorIndex.hfresh(search_probe=100))

    config = collection.config.get()
    assert isinstance(config.vector_index_config, _VectorIndexConfigHFresh)
    assert config.vector_index_config.max_posting_size_kb == 512
    assert config.vector_index_config.replicas == 1
    assert config.vector_index_config.search_probe == 100


def test_collection_hfresh_export_and_reimport(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 36, 0):
        pytest.skip("Hfresh index is not supported in Weaviate versions lower than 1.36.0")

    collection = collection_factory(
        vector_index_config=Configure.VectorIndex.hfresh(
            distance_metric=VectorDistances.COSINE,
            max_posting_size_kb=1024,
            replicas=2,
            search_probe=50,
        )
    )

    config = collection.config.get()

    name = f"TestHFreshExportAndReimport_{collection.name}"
    config.name = name
    with weaviate.connect_to_local() as client:
        client.collections.delete(name)
        client.collections.create_from_dict(config.to_dict())
        new = client.collections.use(name).config.get()
        assert config == new
        assert config.to_dict() == new.to_dict()
        client.collections.delete(name)


def test_collection_hfresh_multi_vector_muvera(collection_factory: CollectionFactory) -> None:
    collection_dummy = collection_factory("dummy")
    if collection_dummy._connection._weaviate_version.is_lower_than(1, 40, 0):
        pytest.skip("Multi-vector HFresh is not supported in Weaviate versions lower than 1.40.0")

    collection = collection_factory(
        vector_config=[
            Configure.MultiVectors.self_provided(
                name="colbert",
                encoding=Configure.VectorIndex.MultiVector.Encoding.muvera(
                    ksim=4, dprojections=16, repetitions=10
                ),
                vector_index_config=Configure.VectorIndex.hfresh(),
            ),
        ],
    )

    config = collection.config.get()

    assert config.vector_config is not None
    index_config = config.vector_config["colbert"].vector_index_config
    assert isinstance(index_config, _VectorIndexConfigHFresh)
    assert index_config.multi_vector is not None
    assert isinstance(index_config.multi_vector.encoding, _MuveraConfig)
    assert index_config.multi_vector.encoding.ksim == 4
    assert index_config.multi_vector.encoding.dprojections == 16
    assert index_config.multi_vector.encoding.repetitions == 10

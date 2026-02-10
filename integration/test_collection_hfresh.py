import pytest
import weaviate
import weaviate.exceptions
from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    VectorDistances,
    VectorIndexType,
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

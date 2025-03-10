

import uuid
from typing import Generator
import numpy as np
import pytest
import weaviate
from integration.conftest import CollectionFactory
from weaviate.collections.classes.config import (
    Configure,
    Reconfigure,
    DataType,
    Property,
    VectorIndexType,
    CUVSBuildAlgo,
    CUVSSearchAlgo,
    CUVSIndexLocation,
    VectorIndexConfigCUVS,
    _VectorIndexConfigCUVS,
)
import time
from weaviate.collections.classes.grpc import MetadataQuery
from weaviate.collections.classes.data import DataObject



@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.connect_to_local(port=8087)
    # client.collections.delete_all()
    yield client
    # client.collections.delete_all()
    client.close()


def test_cuvs_create_config(collection_factory: CollectionFactory) -> None:
    """Test creating a collection with CUVS index configuration."""
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.cuvs(
            graph_degree=32,
            intermediate_graph_degree=32,
            build_algo=CUVSBuildAlgo.NN_DESCENT,
            search_algo=CUVSSearchAlgo.MULTI_CTA,
            itop_k_size=256,
            search_width=1,
        ),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    
    

    
    # Now verify the configuration
    config = collection.config.get()
    print("COLLECTION TYPE")
    print(config)
    print("TYPE")
    print(type(config.vector_index_config))
    
    if isinstance(config.vector_index_config, _VectorIndexConfigCUVS):
        assert config.vector_index_config.graph_degree == 32
        assert config.vector_index_config.intermediate_graph_degree == 32
        assert config.vector_index_config.build_algo == CUVSBuildAlgo.NN_DESCENT
        assert config.vector_index_config.search_algo == CUVSSearchAlgo.MULTI_CTA
        assert config.vector_index_config.itop_k_size == 256
        assert config.vector_index_config.search_width == 1
    else:
        assert False
            

   


def test_cuvs_search(collection_factory: CollectionFactory) -> None:
    """Test vector search with CUVS index."""
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.cuvs(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    
    # Insert test data - CUVS requires at least 32 vectors
    dim = 1536
    num_vectors = 1024
    vectors = [
        np.random.rand(dim).astype(np.float32) for _ in range(num_vectors)
        
    ]
    
    with collection.batch.fixed_size(batch_size=128, concurrent_requests=1) as batch:
        for i in range(num_vectors):
            batch.add_object(properties={"name": f"item{i}"}, vector=vectors[i])
            if batch.number_errors > 10:
                print("Batch import stopped due to excessive errors.")
                break
        
    collection.batch.wait_for_vector_indexing()
    


    failed_objects = collection.batch.failed_objects
    if failed_objects:
        print(f"Number of failed imports: {len(failed_objects)}")
        print(f"First failed object: {failed_objects[0]}")
    else:
        print("No failed imports.")
    assert(len(failed_objects) == 0)
    
    # Query nearest neighbors
    query_vector = vectors[0]  # Use first vector as query
    results = collection.query.near_vector(
        query_vector,
        limit=2,
        return_metadata=MetadataQuery(distance=True)
    ).objects
    
    assert len(results) == 2
    # First result should be the query vector itself (or very close to it)
    assert results[0].metadata.distance == pytest.approx(0.0, abs=1e-6)


def test_cuvs_convert_search(collection_factory: CollectionFactory) -> None:
    """Test vector search with CUVS index."""
    collection = collection_factory(
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.cuvs(),
        properties=[
            Property(name="name", data_type=DataType.TEXT),
        ],
    )
    
    # Insert test data - CUVS requires at least 32 vectors
    dim = 1536
    num_vectors = 1024
    vectors = [
        np.random.rand(dim).astype(np.float32) for _ in range(num_vectors)
        
    ]
    
    with collection.batch.fixed_size(batch_size=128, concurrent_requests=1) as batch:
        for i in range(num_vectors):
            batch.add_object(properties={"name": f"item{i}"}, vector=vectors[i])
            if batch.number_errors > 10:
                print("Batch import stopped due to excessive errors.")
                break
        
    collection.batch.wait_for_vector_indexing()
    
    
    
    collection.config.update(vectorizer_config=Reconfigure.VectorIndex.cuvs(search_width=8))
    collection.config.update(vectorizer_config=Reconfigure.VectorIndex.cuvs(index_location=CUVSIndexLocation.CPU))
    collection.config.update(vectorizer_config=Reconfigure.VectorIndex.cuvs(index_location=CUVSIndexLocation.GPU))

    failed_objects = collection.batch.failed_objects
    if failed_objects:
        print(f"Number of failed imports: {len(failed_objects)}")
        print(f"First failed object: {failed_objects[0]}")
    else:
        print("No failed imports.")
    assert(len(failed_objects) == 0)
    
    # Query nearest neighbors
    query_vector = vectors[0]  # Use first vector as query
    results = collection.query.near_vector(
        query_vector,
        limit=2,
        return_metadata=MetadataQuery(distance=True)
    ).objects
    
    assert len(results) == 2
    # First result should be the query vector itself (or very close to it)
    assert results[0].metadata.distance == pytest.approx(0.0, abs=1e-6)
import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.query import Diversity
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.collections.classes.data import DataObject


def _create_clustered_collection(collection_factory: CollectionFactory):
    """Create a collection with 3 tight clusters (a, b, c) of vectors in 3D."""
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    if collection._connection._weaviate_version.is_lower_than(1, 37, 0):
        pytest.skip("Diversity selection requires Weaviate >= 1.37.0")
    collection.data.insert_many(
        [
            DataObject(properties={"text": "a1"}, vector=[1.0, 0.0, 0.0]),
            DataObject(properties={"text": "a2"}, vector=[0.95, 0.05, 0.0]),
            DataObject(properties={"text": "a3"}, vector=[0.9, 0.1, 0.0]),
            DataObject(properties={"text": "b1"}, vector=[0.0, 1.0, 0.0]),
            DataObject(properties={"text": "b2"}, vector=[0.05, 0.95, 0.0]),
            DataObject(properties={"text": "c1"}, vector=[0.0, 0.0, 1.0]),
        ]
    )
    return collection


def test_near_vector_diversity_selection(collection_factory: CollectionFactory) -> None:
    """Verify that the client passes diversity_selection to the server correctly.

    Two orthogonal assertions — server-side logic (MMR itself) is out of scope:
    - ``balance`` reaches the server: balance=0.0 produces a different UUID ordering than balance=1.0
    - ``limit`` reaches the server: len(result) == mmr_limit
    """
    collection = _create_clustered_collection(collection_factory)
    mmr_limit = 3

    balance_0 = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=Diversity.mmr(limit=mmr_limit, balance=0.0),
    ).objects
    balance_1 = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=Diversity.mmr(limit=mmr_limit, balance=1.0),
    ).objects

    # mmr_limit reaches the server → result count equals it
    assert len(balance_0) == mmr_limit
    assert len(balance_1) == mmr_limit
    # balance reaches the server → different ordering
    assert [o.uuid for o in balance_0] != [o.uuid for o in balance_1]


def test_near_text_diversity_selection(collection_factory: CollectionFactory) -> None:
    """Smoke test: diversity_selection kwarg is wired through the near_text entry point."""
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
    )
    if collection._connection._weaviate_version.is_lower_than(1, 37, 0):
        pytest.skip("Diversity selection requires Weaviate >= 1.37.0")
    for name in ["banana", "apple", "orange", "car", "truck", "bike"]:
        collection.data.insert({"name": name})

    result = collection.query.near_text(
        query="fruit",
        diversity_selection=Diversity.mmr(limit=3, balance=0.5),
    )
    assert len(result.objects) == 3


def test_near_object_diversity_selection(collection_factory: CollectionFactory) -> None:
    """Smoke test: diversity_selection kwarg is wired through the near_object entry point."""
    collection = _create_clustered_collection(collection_factory)
    anchor = next(iter(collection.query.fetch_objects().objects)).uuid

    result = collection.query.near_object(
        near_object=anchor,
        diversity_selection=Diversity.mmr(limit=3, balance=0.5),
    )
    assert len(result.objects) == 3


def test_generate_diversity_selection(collection_factory: CollectionFactory) -> None:
    """Smoke test: diversity_selection kwarg is wired through the .generate namespace."""
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        generative_config=Configure.Generative.custom("generative-dummy"),
    )
    if collection._connection._weaviate_version.is_lower_than(1, 37, 0):
        pytest.skip("Diversity selection requires Weaviate >= 1.37.0")
    for name in ["banana", "apple", "orange", "car", "truck", "bike"]:
        collection.data.insert({"name": name})

    result = collection.generate.near_text(
        query="fruit",
        single_prompt="Describe {name}",
        diversity_selection=Diversity.mmr(limit=3, balance=0.5),
    )
    assert len(result.objects) == 3


def test_diversity_selection_api_surface() -> None:
    """Test the public API surface of Diversity: factory guard + mmr factory method."""
    # Direct instantiation of the factory class fails
    with pytest.raises(TypeError):
        Diversity()

    # Diversity.mmr() produces an MMR-configured selection object
    assert Diversity.mmr(limit=3, balance=0.5).limit == 3

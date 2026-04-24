import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.query import DiversitySelection
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


def test_near_vector_diversity_pure_relevance(
    collection_factory: CollectionFactory,
) -> None:
    """balance=1.0 -> MMR degenerates to pure relevance (same as no diversity)."""
    collection = _create_clustered_collection(collection_factory)

    baseline = collection.query.near_vector(near_vector=[1.0, 0.0, 0.0], limit=3).objects
    diverse = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=DiversitySelection.mmr(limit=3, balance=1.0),
    ).objects

    assert [o.properties["text"] for o in baseline] == [o.properties["text"] for o in diverse]


def test_near_vector_diversity_pure_diversity(
    collection_factory: CollectionFactory,
) -> None:
    """balance=0.0 -> MMR picks maximally diverse results (one per cluster)."""
    collection = _create_clustered_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
    )
    texts = {o.properties["text"] for o in result.objects}
    assert len(texts) == 3
    # Pure diversity should pick one from each cluster (a*, b*, c*)
    clusters = {t[0] for t in texts}
    assert clusters == {"a", "b", "c"}


def test_near_vector_diversity_with_mmr_class(
    collection_factory: CollectionFactory,
) -> None:
    """Direct MMR class construction (DiversitySelection.MMR) also works, not just the factory."""
    collection = _create_clustered_collection(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=DiversitySelection.MMR(limit=3, balance=0.0),
    )
    clusters = {o.properties["text"][0] for o in result.objects}
    assert clusters == {"a", "b", "c"}


def test_near_object_diversity(collection_factory: CollectionFactory) -> None:
    """near_object supports diversity selection."""
    collection = _create_clustered_collection(collection_factory)
    anchor = next(iter(collection.query.fetch_objects().objects)).uuid

    result = collection.query.near_object(
        near_object=anchor,
        diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
    )
    assert len(result.objects) == 3
    clusters = {o.properties["text"][0] for o in result.objects}
    assert len(clusters) == 3


def test_diversity_cannot_be_instantiated() -> None:
    """Test that direct instantiation of the DiversitySelection factory fails."""
    with pytest.raises(TypeError):
        DiversitySelection()


def test_diversity_mmr_only_limit(collection_factory: CollectionFactory) -> None:
    """MMR accepts just a limit (balance defaults to server-side value)."""
    collection = _create_clustered_collection(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=DiversitySelection.mmr(limit=2),
    )
    assert len(result.objects) == 2


def test_near_text_diversity(collection_factory: CollectionFactory) -> None:
    """near_text supports diversity selection via text2vec-contextionary."""
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
        diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
    )
    assert len(result.objects) == 3


def test_near_vector_balance_0_differs_from_balance_1(
    collection_factory: CollectionFactory,
) -> None:
    """Test that MMR balance=0 (pure diversity) produces a different ordering than balance=1."""
    collection = _create_clustered_collection(collection_factory)
    balance_0 = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
    ).objects
    balance_1 = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        diversity_selection=DiversitySelection.mmr(limit=3, balance=1.0),
    ).objects
    assert [o.uuid for o in balance_0] != [o.uuid for o in balance_1]


def test_near_text_generate_diversity(collection_factory: CollectionFactory) -> None:
    """Generate namespace (collection.generate.near_text) also supports diversity selection."""
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
        diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
    )
    assert len(result.objects) == 3

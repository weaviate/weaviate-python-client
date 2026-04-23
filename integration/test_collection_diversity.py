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
    if collection._connection._weaviate_version.is_lower_than(1, 37, 1):
        pytest.skip("Diversity selection requires Weaviate >= 1.37.1")
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
        selection=Diversity.MMR(limit=3, balance=1.0),
    ).objects

    assert [o.properties["text"] for o in baseline] == [o.properties["text"] for o in diverse]


def test_near_vector_diversity_pure_diversity(
    collection_factory: CollectionFactory,
) -> None:
    """balance=0.0 -> MMR picks maximally diverse results (one per cluster)."""
    collection = _create_clustered_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        selection=Diversity.MMR(limit=3, balance=0.0),
    )
    texts = {o.properties["text"] for o in result.objects}
    assert len(texts) == 3
    # Pure diversity should pick one from each cluster (a*, b*, c*)
    clusters = {t[0] for t in texts}
    assert clusters == {"a", "b", "c"}


def test_near_object_diversity(collection_factory: CollectionFactory) -> None:
    """near_object supports diversity selection."""
    collection = _create_clustered_collection(collection_factory)
    anchor = next(iter(collection.query.fetch_objects().objects)).uuid

    result = collection.query.near_object(
        near_object=anchor,
        selection=Diversity.MMR(limit=3, balance=0.0),
    )
    assert len(result.objects) == 3
    clusters = {o.properties["text"][0] for o in result.objects}
    assert len(clusters) == 3


def test_diversity_cannot_be_instantiated() -> None:
    """Diversity is a factory — direct instantiation should fail."""
    with pytest.raises(TypeError):
        Diversity()


def test_diversity_mmr_only_limit(collection_factory: CollectionFactory) -> None:
    """MMR accepts just a limit (balance defaults to server-side value)."""
    collection = _create_clustered_collection(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        selection=Diversity.MMR(limit=2),
    )
    assert len(result.objects) == 2

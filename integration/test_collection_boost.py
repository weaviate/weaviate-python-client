import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.query import Boost, Filter, MetadataQuery
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.collections.classes.data import DataObject


def _create_collection(collection_factory: CollectionFactory):
    """Create a collection with numeric and date properties for boost testing."""
    collection = collection_factory(
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="price", data_type=DataType.NUMBER),
            Property(name="rating", data_type=DataType.NUMBER),
            Property(name="count", data_type=DataType.INT),
            Property(name="created", data_type=DataType.DATE),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
        vector_index_config=Configure.VectorIndex.flat(),
    )
    if collection._connection._weaviate_version.is_lower_than(1, 38, 0):
        pytest.skip("Boost requires Weaviate >= 1.38.0")
    collection.data.insert_many(
        [
            DataObject(
                properties={
                    "text": "cheap good",
                    "price": 10.0,
                    "rating": 4.9,
                    "count": 1000,
                    "created": "2024-01-01T00:00:00Z",
                },
                vector=[1.0, 0.0, 0.0],
            ),
            DataObject(
                properties={
                    "text": "cheap bad",
                    "price": 10.0,
                    "rating": 2.0,
                    "count": 5,
                    "created": "2020-01-01T00:00:00Z",
                },
                vector=[0.9, 0.1, 0.0],
            ),
            DataObject(
                properties={
                    "text": "expensive good",
                    "price": 500.0,
                    "rating": 4.8,
                    "count": 500,
                    "created": "2023-06-01T00:00:00Z",
                },
                vector=[0.0, 1.0, 0.0],
            ),
            DataObject(
                properties={
                    "text": "expensive bad",
                    "price": 500.0,
                    "rating": 1.5,
                    "count": 2,
                    "created": "2019-01-01T00:00:00Z",
                },
                vector=[0.0, 0.9, 0.1],
            ),
            DataObject(
                properties={
                    "text": "mid range",
                    "price": 50.0,
                    "rating": 3.5,
                    "count": 100,
                    "created": "2022-01-01T00:00:00Z",
                },
                vector=[0.0, 0.0, 1.0],
            ),
        ]
    )
    return collection


def test_boost_filter(collection_factory: CollectionFactory) -> None:
    """Boost results matching a filter — boosted items should score higher."""
    collection = _create_collection(collection_factory)

    baseline = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        return_metadata=MetadataQuery(distance=True),
    ).objects

    boosted = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.filter(
            Filter.by_property("rating").greater_or_equal(4.0),
            weight=1.0,
        ),
        return_metadata=MetadataQuery(distance=True),
    ).objects

    assert len(boosted) == 5
    # The boost should change the ordering compared to baseline
    assert [o.uuid for o in baseline] != [o.uuid for o in boosted]


def test_boost_numeric_decay(collection_factory: CollectionFactory) -> None:
    """Numeric decay: prefer items with price near the origin."""
    collection = _create_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.numeric_decay(
            "price",
            origin=50.0,
            scale=20.0,
            curve=Boost.Curve.LINEAR,
            decay=0.5,
            weight=1.0,
        ),
        return_metadata=MetadataQuery(distance=True),
    ).objects

    assert len(result) == 5


def test_boost_time_decay(collection_factory: CollectionFactory) -> None:
    """Time decay: prefer items with dates closer to origin."""
    collection = _create_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.time_decay(
            "created",
            origin="2024-01-01T00:00:00Z",
            scale="365d",
            curve=Boost.Curve.EXPONENTIAL,
            decay=0.3,
            weight=1.0,
        ),
        return_metadata=MetadataQuery(distance=True),
    ).objects

    assert len(result) == 5


def test_boost_property_value(collection_factory: CollectionFactory) -> None:
    """Property value boost: rank by a numeric property directly."""
    collection = _create_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.numeric_property(
            "count",
            modifier=Boost.Modifier.LOG1P,
            weight=1.0,
        ),
        return_metadata=MetadataQuery(distance=True),
    ).objects

    assert len(result) == 5


def test_boost_blend(collection_factory: CollectionFactory) -> None:
    """Blend multiple boost conditions together."""
    collection = _create_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.blend(
            [
                Boost.filter(
                    Filter.by_property("rating").greater_or_equal(4.0),
                    weight=2.0,
                ),
                Boost.numeric_decay(
                    "price",
                    origin=30.0,
                    scale=100.0,
                    curve=Boost.Curve.EXPONENTIAL,
                ),
            ],
            weight=0.8,
        ),
        return_metadata=MetadataQuery(distance=True),
    ).objects

    assert len(result) == 5


def test_boost_with_depth(collection_factory: CollectionFactory) -> None:
    """Boost with explicit depth parameter."""
    collection = _create_collection(collection_factory)

    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.filter(
            Filter.by_property("rating").greater_or_equal(4.0),
            weight=1.0,
            depth=100,
        ),
        return_metadata=MetadataQuery(distance=True),
    ).objects

    assert len(result) == 5


def test_boost_bm25(collection_factory: CollectionFactory) -> None:
    """Boost works with BM25 keyword search."""
    collection = _create_collection(collection_factory)

    result = collection.query.bm25(
        query="cheap",
        limit=5,
        boost=Boost.filter(
            Filter.by_property("rating").greater_or_equal(4.0),
            weight=1.0,
        ),
        return_metadata=MetadataQuery(score=True),
    ).objects

    assert len(result) >= 1


def test_boost_hybrid(collection_factory: CollectionFactory) -> None:
    """Boost works with hybrid search."""
    collection = _create_collection(collection_factory)

    result = collection.query.hybrid(
        query="cheap",
        vector=[1.0, 0.0, 0.0],
        limit=5,
        boost=Boost.filter(
            Filter.by_property("price").less_than(100.0),
            weight=0.6,
        ),
        return_metadata=MetadataQuery(score=True),
    ).objects

    assert len(result) >= 1


def test_boost_api_surface() -> None:
    """Test the public API surface: factory guard + static methods."""
    with pytest.raises(TypeError):
        Boost()

    # Static methods produce _Boost instances
    b = Boost.filter(
        Filter.by_property("x").equal("y"),
        weight=0.5,
    )
    assert len(b.conditions) == 1
    assert b.weight == 0.5

    b = Boost.blend(
        [
            Boost.filter(Filter.by_property("x").equal("y"), weight=1.0),
            Boost.numeric_property("z", modifier=Boost.Modifier.LOG1P),
        ],
        weight=0.8,
        depth=200,
    )
    assert len(b.conditions) == 2
    assert b.weight == 0.8
    assert b.depth == 200

    # blend() also accepts a single boost
    b = Boost.blend(Boost.filter(Filter.by_property("x").equal("y")), weight=0.5)
    assert len(b.conditions) == 1
    assert b.weight == 0.5


def test_boost_blend_rejects_sub_boost_depth() -> None:
    """blend() raises if any sub-boost has depth set."""
    with pytest.raises(WeaviateInvalidInputError):
        Boost.blend(
            Boost.numeric_property("count", depth=500),
            depth=100,
        )


def test_boost_default_curve_is_unspecified() -> None:
    """Omitting curve defaults to None (sent as UNSPECIFIED on the wire)."""
    b = Boost.numeric_decay("price", origin=50.0, scale=20.0)
    assert b.conditions[0].numeric_decay.curve is None

    b = Boost.time_decay("created", scale="7d")
    assert b.conditions[0].time_decay.curve is None


def test_boost_default_modifier_is_unspecified() -> None:
    """Omitting modifier defaults to None (sent as UNSPECIFIED on the wire)."""
    b = Boost.numeric_property("count")
    assert b.conditions[0].property_value.modifier is None

import pytest

from test.collection.schema import multi_vector_schema, single_vector_schema
from weaviate.collections.classes.config import (
    Reconfigure,
    _CollectionConfigUpdate,
)
from weaviate.exceptions import WeaviateInvalidInputError


@pytest.mark.parametrize(
    "schema,should_error",
    [
        (multi_vector_schema(), False),
        (multi_vector_schema("bq"), True),
        (multi_vector_schema("sq"), True),
    ],
)
def test_enabling_pq_multi_vector(schema: dict, should_error: bool) -> None:
    update = _CollectionConfigUpdate(
        vectorizer_config=[
            Reconfigure.NamedVectors.update(
                name="boi",
                vector_index_config=Reconfigure.VectorIndex.hnsw(
                    quantizer=Reconfigure.VectorIndex.Quantizer.pq()
                ),
            )
        ]
    )
    if should_error:
        with pytest.raises(WeaviateInvalidInputError):
            update.merge_with_existing(schema)
        return

    new_schema = update.merge_with_existing(schema)

    assert new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["pq"]["enabled"]
    assert not new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["bq"]["enabled"]
    assert not new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["sq"]["enabled"]

    assert new_schema["vectorConfig"]["yeh"] == schema["vectorConfig"]["yeh"]


@pytest.mark.parametrize(
    "schema,should_error",
    [
        (multi_vector_schema(), False),
        (multi_vector_schema("pq"), True),
        (multi_vector_schema("sq"), True),
    ],
)
def test_enabling_bq_multi_vector(schema: dict, should_error: bool) -> None:
    update = _CollectionConfigUpdate(
        vectorizer_config=[
            Reconfigure.NamedVectors.update(
                name="boi",
                vector_index_config=Reconfigure.VectorIndex.hnsw(
                    quantizer=Reconfigure.VectorIndex.Quantizer.bq()
                ),
            )
        ]
    )
    if should_error:
        with pytest.raises(WeaviateInvalidInputError):
            update.merge_with_existing(schema)
        return

    new_schema = update.merge_with_existing(schema)

    assert not new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["pq"]["enabled"]
    assert new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["bq"]["enabled"]
    assert not new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["sq"]["enabled"]

    assert new_schema["vectorConfig"]["yeh"] == schema["vectorConfig"]["yeh"]


@pytest.mark.parametrize(
    "schema,should_error",
    [
        (multi_vector_schema(), False),
        (multi_vector_schema("pq"), True),
        (multi_vector_schema("bq"), True),
    ],
)
def test_enabling_sq_multi_vector(schema: dict, should_error: bool) -> None:
    update = _CollectionConfigUpdate(
        vectorizer_config=[
            Reconfigure.NamedVectors.update(
                name="boi",
                vector_index_config=Reconfigure.VectorIndex.hnsw(
                    quantizer=Reconfigure.VectorIndex.Quantizer.sq()
                ),
            )
        ]
    )
    if should_error:
        with pytest.raises(WeaviateInvalidInputError):
            update.merge_with_existing(schema)
        return

    new_schema = update.merge_with_existing(schema)

    assert not new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["pq"]["enabled"]
    assert not new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["bq"]["enabled"]
    assert new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["sq"]["enabled"]

    assert new_schema["vectorConfig"]["yeh"] == schema["vectorConfig"]["yeh"]


def test_replication_async_config_replace_on_update() -> None:
    """Test asyncConfig is replaced (not merged) when provided in an update."""
    schema = {
        "factor": 1,
        "asyncEnabled": True,
        "asyncConfig": {"maxWorkers": 8, "hashtreeHeight": 20},
    }
    update = Reconfigure.replication(
        async_config=Reconfigure.Replication.async_config(max_workers=16),
    )
    result = update.merge_with_existing(schema)
    assert result["asyncConfig"] == {"maxWorkers": 16}
    assert "hashtreeHeight" not in result["asyncConfig"]


def test_replication_async_config_cleared_when_async_disabled() -> None:
    """Test asyncConfig is removed from schema when asyncEnabled is set to False."""
    schema = {
        "factor": 1,
        "asyncEnabled": True,
        "asyncConfig": {"maxWorkers": 8, "hashtreeHeight": 20},
    }
    update = Reconfigure.replication(async_enabled=False)
    result = update.merge_with_existing(schema)
    assert result["asyncEnabled"] is False
    assert "asyncConfig" not in result


def test_replication_async_config_preserved_when_not_provided() -> None:
    """Test asyncConfig is preserved when not provided in update."""
    schema = {
        "factor": 1,
        "asyncEnabled": True,
        "asyncConfig": {"maxWorkers": 8, "hashtreeHeight": 20},
    }
    update = Reconfigure.replication(factor=2)
    result = update.merge_with_existing(schema)
    assert result["factor"] == 2
    assert result["asyncConfig"] == {"maxWorkers": 8, "hashtreeHeight": 20}


def test_replication_async_config_reset_all_fields() -> None:
    """Passing empty async_config should replace with empty dict (server uses defaults)."""
    schema = {
        "factor": 1,
        "asyncEnabled": True,
        "asyncConfig": {"maxWorkers": 8, "hashtreeHeight": 20},
    }
    update = Reconfigure.replication(
        async_config=Reconfigure.Replication.async_config(),
    )
    result = update.merge_with_existing(schema)
    assert result["asyncConfig"] == {}


# Regression tests for https://github.com/weaviate/weaviate-python-client/issues/1277
# Changing the vector index *type* of an existing collection is server-side immutable. Previously
# such an attempt was silently ignored, leaving users to believe the change had been applied.


def test_changing_vector_index_type_single_vector_raises() -> None:
    """Reproduces #1277: updating a flat index to a dynamic index must raise, not silently no-op."""
    schema = single_vector_schema("flat")
    update = _CollectionConfigUpdate(
        vectorizer_config=Reconfigure.VectorIndex.dynamic(),
    )
    with pytest.raises(WeaviateInvalidInputError, match="immutable"):
        update.merge_with_existing(schema)


def test_changing_vector_index_type_via_vector_index_config_raises() -> None:
    """The deprecated `vector_index_config` argument must also reject a type change."""
    schema = single_vector_schema("flat")
    update = _CollectionConfigUpdate(
        vector_index_config=Reconfigure.VectorIndex.hnsw(),
    )
    with pytest.raises(WeaviateInvalidInputError, match="immutable"):
        update.merge_with_existing(schema)


def test_same_vector_index_type_single_vector_still_updates() -> None:
    """A normal, allowed update to the same (flat) index type still merges successfully."""
    schema = single_vector_schema("flat")
    update = _CollectionConfigUpdate(
        vectorizer_config=Reconfigure.VectorIndex.flat(vector_cache_max_objects=42),
    )
    new_schema = update.merge_with_existing(schema)
    assert new_schema["vectorIndexType"] == "flat"
    assert new_schema["vectorIndexConfig"]["vectorCacheMaxObjects"] == 42


def test_changing_vector_index_type_named_vector_raises() -> None:
    """Changing an existing named (hnsw) vector to flat must raise rather than silently no-op."""
    schema = multi_vector_schema()
    update = _CollectionConfigUpdate(
        vectorizer_config=[
            Reconfigure.NamedVectors.update(
                name="boi",
                vector_index_config=Reconfigure.VectorIndex.flat(),
            )
        ]
    )
    with pytest.raises(WeaviateInvalidInputError, match="immutable"):
        update.merge_with_existing(schema)


def test_changing_vector_index_type_vector_config_raises() -> None:
    """Changing an existing (hnsw) vector to dynamic via `vector_config` must raise."""
    schema = multi_vector_schema()
    update = _CollectionConfigUpdate(
        vector_config=Reconfigure.Vectors.update(
            name="boi",
            vector_index_config=Reconfigure.VectorIndex.dynamic(),
        )
    )
    with pytest.raises(WeaviateInvalidInputError, match="immutable"):
        update.merge_with_existing(schema)


def test_same_vector_index_type_named_vector_still_updates() -> None:
    """A normal, allowed update to the same (hnsw) named vector index still merges successfully."""
    schema = multi_vector_schema()
    update = _CollectionConfigUpdate(
        vectorizer_config=[
            Reconfigure.NamedVectors.update(
                name="boi",
                vector_index_config=Reconfigure.VectorIndex.hnsw(ef=128),
            )
        ]
    )
    new_schema = update.merge_with_existing(schema)
    assert new_schema["vectorConfig"]["boi"]["vectorIndexType"] == "hnsw"
    assert new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["ef"] == 128
    assert new_schema["vectorConfig"]["yeh"] == schema["vectorConfig"]["yeh"]

import pytest

from test.collection.schema import multi_vector_schema
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


@pytest.mark.parametrize("use_deprecated_syntax", [False, True])
def test_updating_dropped_vector_index(use_deprecated_syntax: bool) -> None:
    """A vector whose index was dropped has no index config to merge into."""
    schema = multi_vector_schema()
    # shape reported by Weaviate for a vector dropped via `config.delete_vector_index`
    schema["vectorConfig"]["boi"] = {"vectorizer": {"none": {}}, "vectorIndexType": "none"}

    hnsw = Reconfigure.VectorIndex.hnsw(ef=128)
    update = (
        _CollectionConfigUpdate(
            vectorizer_config=[
                Reconfigure.NamedVectors.update(name="boi", vector_index_config=hnsw)
            ]
        )
        if use_deprecated_syntax
        else _CollectionConfigUpdate(
            vector_config=[Reconfigure.Vectors.update(name="boi", vector_index_config=hnsw)]
        )
    )

    with pytest.raises(WeaviateInvalidInputError, match="delete_vector_index"):
        update.merge_with_existing(schema)


def test_updating_vector_next_to_dropped_vector_index() -> None:
    """Vectors that still have an index remain updatable next to a dropped one."""
    schema = multi_vector_schema()
    schema["vectorConfig"]["boi"] = {"vectorizer": {"none": {}}, "vectorIndexType": "none"}

    update = _CollectionConfigUpdate(
        vector_config=[
            Reconfigure.Vectors.update(
                name="yeh", vector_index_config=Reconfigure.VectorIndex.hnsw(ef=128)
            )
        ]
    )
    new_schema = update.merge_with_existing(schema)

    assert new_schema["vectorConfig"]["yeh"]["vectorIndexConfig"]["ef"] == 128
    assert new_schema["vectorConfig"]["boi"] == {
        "vectorizer": {"none": {}},
        "vectorIndexType": "none",
    }

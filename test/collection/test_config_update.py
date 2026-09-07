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


def _hfresh_schema(rescore_limit: int = 20) -> dict:
    """An HFresh schema, which mandates RQ and so carries no pq/bq/sq blocks."""
    return {
        "class": "HFreshRQ",
        "vectorConfig": {
            "boi": {
                "vectorizer": {"text2vec-weaviate": {}},
                "vectorIndexType": "hfresh",
                "vectorIndexConfig": {
                    "distance": "cosine",
                    "maxPostingSizeKB": 1024,
                    "searchProbe": 8,
                    "rq": {"enabled": True, "bits": 1, "rescoreLimit": rescore_limit},
                },
            }
        },
    }


def test_updating_rq_on_hfresh_without_pq_block() -> None:
    """An HFresh schema has no pq block, so the quantizer check must not subscript it."""
    schema = _hfresh_schema()
    update = _CollectionConfigUpdate(
        vector_config=Reconfigure.Vectors.update(
            name="boi",
            vector_index_config=Reconfigure.VectorIndex.hfresh(
                quantizer=Reconfigure.VectorIndex.Quantizer.rq(rescore_limit=500)
            ),
        )
    )

    new_schema = update.merge_with_existing(schema)

    assert new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["rq"]["rescoreLimit"] == 500
    assert new_schema["vectorConfig"]["boi"]["vectorIndexConfig"]["rq"]["enabled"]


def test_quantizer_check_tolerates_missing_pq_block() -> None:
    """The rq branch of the quantizer check must tolerate a schema with no pq block."""
    schema = _hfresh_schema()
    update = _CollectionConfigUpdate(
        vector_config=Reconfigure.Vectors.update(
            name="boi",
            vector_index_config=Reconfigure.VectorIndex.hfresh(
                quantizer=Reconfigure.VectorIndex.Quantizer.rq()
            ),
        )
    )

    # No KeyError: rq is the quantizer already in use, so the update is allowed through.
    update.merge_with_existing(schema)


def test_switching_quantizer_still_rejected_when_pq_enabled() -> None:
    """The guard itself must be unchanged for schemas that do have a pq block."""
    schema = multi_vector_schema("pq")
    update = _CollectionConfigUpdate(
        vectorizer_config=[
            Reconfigure.NamedVectors.update(
                name="boi",
                vector_index_config=Reconfigure.VectorIndex.hnsw(
                    quantizer=Reconfigure.VectorIndex.Quantizer.rq()
                ),
            )
        ]
    )
    with pytest.raises(WeaviateInvalidInputError):
        update.merge_with_existing(schema)

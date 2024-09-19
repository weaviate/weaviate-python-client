import pytest

from test.collection.schema import multi_vector_schema
from weaviate.collections.classes.config import _CollectionConfigUpdate, Reconfigure
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

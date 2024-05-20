import numpy as np
import pandas as pd
import polars as pl
from weaviate.util import _get_vector_v4

# Don't need to test `tf` or `torch` tensors since `_get_vector_v4`` converts them to `np` first


def test_get_vector_v4_with_np_array_and_np_float() -> None:
    # Assert that np.array[np.float32] -> list[float]
    vec = _get_vector_v4(np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float32))
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)


def test_get_vector_v4_with_list_and_np_float() -> None:
    # Assert that list[np.float32] -> list[np.float32]
    vec = _get_vector_v4(list(np.array([0.12345] * 1536, dtype=np.float32)))
    assert isinstance(vec, list)
    assert all(isinstance(e, np.float32) for e in vec)


def test_get_vector_v4_with_list() -> None:
    # Assert that list[float] -> list[float]
    vec = _get_vector_v4([1.0, 2.0, 3.0, 4.0, 5.0])
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)


def test_get_vector_v4_with_pd() -> None:
    # Assert that pd.Series[pd.Float32Dtype] -> list[float]
    vec = _get_vector_v4(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], dtype="Float32"))
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)


def test_get_vector_v4_with_pl() -> None:
    # Assert that pl.Series[pl.Float32] -> list[float]
    vec = _get_vector_v4(pl.Series("a", [1.0, 2.0, 3.0, 4.0, 5.0], pl.Float32))
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)

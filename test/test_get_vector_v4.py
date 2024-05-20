import numpy as np
import pandas as pd
import polars as pl
from weaviate.util import _get_vector_v4

# Don't need to test `tf` or `torch` tensors since `_get_vector_v4`` converts them to `np` first


def test_get_vector_v4_with_np() -> None:
    vec = _get_vector_v4(np.array([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)


def test_get_vector_v4_with_list() -> None:
    vec = _get_vector_v4([1.0, 2.0, 3.0, 4.0, 5.0])
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)


def test_get_vector_v4_with_pd() -> None:
    vec = _get_vector_v4(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0]))
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)


def test_get_vector_v4_with_pl() -> None:
    vec = _get_vector_v4(pl.Series("a", [1.0, 2.0, 3.0, 4.0, 5.0]))
    assert isinstance(vec, list)
    assert all(isinstance(e, float) for e in vec)

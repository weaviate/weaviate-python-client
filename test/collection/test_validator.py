from typing import Any, List, Sequence, Union

import numpy as np
import pandas as pd
import polars as pl
import pytest

from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.validator import _ExtraTypes, _validate_input, _ValidateArgument


@pytest.mark.parametrize(
    "inputs,expected,error",
    [
        (1, [int], False),
        (1.0, [int], True),
        ([1, 1], [List], False),
        (np.array([1, 2, 3]), [_ExtraTypes.NUMPY], False),
        (np.array([1, 2, 3]), [_ExtraTypes.NUMPY, List], False),
        (np.array([1, 2, 3]), [List], True),
        ([1, 1], [List, _ExtraTypes.NUMPY], False),
        (pd.array([1, 1]), [_ExtraTypes.PANDAS, List], False),
        (pd.Series([1, 1]), [_ExtraTypes.PANDAS, List], False),
        (pl.Series([1, 1]), [_ExtraTypes.POLARS, List], False),
        (
            pl.Series([1, 1]),
            [_ExtraTypes.POLARS, _ExtraTypes.PANDAS, _ExtraTypes.NUMPY, List],
            False,
        ),
        (pl.Series([1, 1]), [_ExtraTypes.PANDAS, _ExtraTypes.NUMPY, List], True),
        # Tests for Sequence[Union[...]] pattern, which was flaky in Python 3.12
        (["a", 1], [Sequence[Union[str, int]]], False),
        ([1, "a"], [Sequence[Union[str, int]]], False),
        ([1, 2], [Sequence[Union[str, int]]], False),
        (["a", "b"], [Sequence[Union[str, int]]], False),
        (["a", 1], [str, Sequence[Union[str, int]]], False),  # matches Sequence[Union[str, int]]
        # Non-sequence values are not valid Sequence types: int is not iterable
        (42, [Sequence[Union[str, int]]], True),
    ],
)
def test_validator(inputs: Any, expected: List[Any], error: bool) -> None:
    if error:
        with pytest.raises(WeaviateInvalidInputError):
            _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))
    else:
        _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))

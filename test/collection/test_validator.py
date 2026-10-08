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
        (True, [int], True),
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
    ],
)
def test_validator(inputs: Any, expected: List[Any], error: bool) -> None:
    if error:
        with pytest.raises(WeaviateInvalidInputError):
            _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))
    else:
        _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))


@pytest.mark.parametrize(
    "inputs,expected,error",
    [
        # every element matches one of the union members -> valid
        (["a", 1, "b", 2], [Sequence[Union[str, int]]], False),
        (["a", "b"], [Sequence[Union[str, int]]], False),
        ([1, 2], [Sequence[Union[str, int]]], False),
        # one element (a float) matches neither union member -> must be rejected.
        # regression test: the old implementation flattened the per-element check
        # into a single any() across (value, union_arg) pairs, so it only took one
        # element matching one type to pass the whole sequence, even if other
        # elements didn't match anything.
        (["a", 3.14], [Sequence[Union[str, int]]], True),
        ([3.14, "a"], [Sequence[Union[str, int]]], True),
        ([1, 3.14], [Sequence[Union[str, int]]], True),
    ],
)
def test_validator_sequence_of_union(inputs: Any, expected: List[Any], error: bool) -> None:
    if error:
        with pytest.raises(WeaviateInvalidInputError):
            _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))
    else:
        _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))

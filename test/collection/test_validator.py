from typing import Any, List

import numpy as np
import pandas as pd
import polars as pl
import pytest

from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.validator import _validate_input, _ValidateArgument, _ExtraTypes


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
    ],
)
def test_validator(inputs: Any, expected: List[Any], error: bool) -> None:
    if error:
        with pytest.raises(WeaviateInvalidInputError):
            _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))
    else:
        _validate_input(_ValidateArgument(expected=expected, name="test", value=inputs))

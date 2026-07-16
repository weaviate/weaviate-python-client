from dataclasses import dataclass
import collections.abc
from typing import Any, List, Sequence, Union, get_args, get_origin

from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.str_enum import BaseEnum


@dataclass
class _ValidateArgument:
    expected: List[Any]
    name: str
    value: Any


class _ExtraTypes(str, BaseEnum):
    NUMPY = "numpy"
    PANDAS = "pandas"
    POLARS = "polars"
    TF = "tensorflow"


def _validate_input(inputs: Union[List[_ValidateArgument], _ValidateArgument]) -> None:
    """Validate the values of the input arguments in comparison to the expected types defined in _ValidateArgument.

    It is not completely robust so be careful supplying subscripted generics in expected as it may not function as expected.
    To avoid this, only supply simply generics like Sequence[...] and List[...] as seen below in __is_valid.
    """
    if isinstance(inputs, _ValidateArgument):
        inputs = [inputs]
    for validate in inputs:
        if not any(_is_valid(exp, validate.value) for exp in validate.expected):
            raise WeaviateInvalidInputError(
                f"Argument '{validate.name}' must be one of: {validate.expected}, but got {type(validate.value)}"
            )


def _is_valid(expected: Any, value: Any) -> bool:
    if expected is None:
        return value is None

    # check for types that are not installed
    # https://stackoverflow.com/questions/12569452/how-to-identify-numpy-types-in-python
    if isinstance(expected, _ExtraTypes):
        return expected.value in type(value).__module__

    expected_origin = get_origin(expected)
    if expected_origin is Union:
        args = get_args(expected)
        return any(isinstance(value, arg) for arg in args)
    
    # FIX for #1355: Use collections.abc.Sequence for robust runtime check in Python 3.12
    if expected_origin is not None and (
        issubclass(expected_origin, collections.abc.Sequence) or expected_origin is list
    ):
        if not isinstance(value, (collections.abc.Sequence, list)):
            return False
        args = get_args(expected)
        if len(args) == 1:
            if get_origin(args[0]) is Union:
                union_args = get_args(args[0])
                # Ensure every element in the sequence matches the Union types
                return all(any(isinstance(val, union_arg) for union_arg in union_args) for val in value)
            else:
                return all(isinstance(val, args[0]) for val in value)
    
    try:
        return isinstance(value, expected)
    except TypeError:
        if expected_origin is not None:
            return isinstance(value, expected_origin)
        return False

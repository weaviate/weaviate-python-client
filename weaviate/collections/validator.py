from dataclasses import dataclass
from typing import Any, List, Sequence, get_args, get_origin

from weaviate.exceptions import WeaviateInvalidInputError


@dataclass
class _ValidateArgument:
    expected: List[Any]
    name: str
    value: Any


def _validate_input(inputs: List[_ValidateArgument]) -> None:
    """Validate the values of the input arguments in comparison to the expected types defined in _ValidateArgument.

    It is not completely robust so be careful supplying subscripted generics in expected as it may not function as expected.
    To avoid this, only supply simply generics like Sequence[...] and List[...] as seen below in __is_valid.
    """
    for validate in inputs:
        if not any(__is_valid(exp, validate.value) for exp in validate.expected):
            raise WeaviateInvalidInputError(
                f"Argument '{validate.name}' must be one of: {validate.expected}, but got {type(validate.value)}"
            )


def __is_valid(expected: Any, value: Any) -> bool:
    if get_origin(expected) == Sequence:
        if not isinstance(value, Sequence):
            return False
        args = get_args(expected)
        return all(isinstance(val, args[0]) for val in value)
    if get_origin(expected) == list:
        if not isinstance(value, list):
            return False
        args = get_args(expected)
        return all(isinstance(val, args[0]) for val in value)
    if expected is None:
        return value is None
    return isinstance(value, expected)

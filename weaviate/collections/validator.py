from typing import Any

from weaviate.exceptions import WeaviateInvalidInputError


def _raise_invalid_input(name: str, value: Any, expected_type: Any) -> None:
    if isinstance(value, list):
        raise WeaviateInvalidInputError(
            f"Argument '{name}' must be {expected_type}, but got typing.List[{' | '.join({type(val).__name__ for val in value})}]"
        )
    else:
        raise WeaviateInvalidInputError(
            f"Argument '{name}' must be {expected_type}, but got {type(value)}"
        )

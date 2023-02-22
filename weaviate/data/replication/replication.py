from enum import Enum, EnumMeta, auto
from typing import Union

from weaviate.util import BaseEnum


class ConsistencyLevel(str, BaseEnum):
    ALL = auto()
    ONE = auto()
    QUORUM = auto()


def name_consistency_level(level: Union[str, ConsistencyLevel]) -> str:
    """
    Returns the name of giving consistency level

    Parameters
    ----------
    level : str or ConsistencyLevel
    Consistency level

    Returns
    -------
    str
        The name of the giving consistency level

    Raises
    ------
    ValueError
        If level is not among valid levels
    """
    if level not in ConsistencyLevel:
        raise ValueError(f"invalid ConsistencyLevel: {level}")
    if isinstance(level, ConsistencyLevel):
        return level.name
    else:
        return level

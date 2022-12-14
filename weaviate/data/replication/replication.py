from enum import Enum, auto


class ConsistencyLevel(str, Enum):
    ALL = auto()
    ONE = auto()
    QUORUM = auto()

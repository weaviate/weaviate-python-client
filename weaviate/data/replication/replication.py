from enum import Enum


class ConsistencyLevel(str, Enum):
    ALL = "ALL"
    ONE = "ONE"
    QUORUM = "QUORUM"

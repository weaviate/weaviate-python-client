from enum import auto

from weaviate.util import BaseEnum


class ConsistencyLevel(str, BaseEnum):
    ALL = auto()
    ONE = auto()
    QUORUM = auto()

from enum import Enum, EnumMeta, auto


# MetaEnum and BaseEnum are required to support `in` statements:
#    'ALL' in ConsistencyLevel == True
#    12345 in ConsistencyLevel == False
class MetaEnum(EnumMeta):
    def __contains__(cls, item):
        try:
            # when item is type ConsistencyLevel
            return item.name in cls.__members__.keys()
        except AttributeError:
            # when item is type str
            return item in cls.__members__.keys()


class BaseEnum(Enum, metaclass=MetaEnum):
    pass


class ConsistencyLevel(str, BaseEnum):
    ALL = auto()
    ONE = auto()
    QUORUM = auto()

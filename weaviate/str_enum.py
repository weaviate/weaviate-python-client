# MetaEnum and BaseEnum are required to support `in` statements:
#    'ALL' in ConsistencyLevel == True
#    12345 in ConsistencyLevel == False
from enum import EnumMeta, Enum
from typing import Any


class MetaEnum(EnumMeta):
    def __contains__(cls, item: Any) -> bool:
        try:
            # when item is type ConsistencyLevel
            return item.name in cls.__members__.keys()
        except AttributeError:
            # when item is type str
            return item in cls.__members__.keys()


class BaseEnum(Enum, metaclass=MetaEnum):
    pass

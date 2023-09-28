from typing import Type, Union
from typing_extensions import TypeAlias
from weaviate.collection.classes.internal import (
    _QueryReturn,
    _GenerativeReturn,
    _GroupByReturn,
    PROPERTIES,
)
from weaviate.collection.classes.types import Properties, TProperties

QueryReturn: TypeAlias = Union[_QueryReturn[Properties], _QueryReturn[TProperties]]
GenerativeReturn: TypeAlias = Union[_GenerativeReturn[Properties], _GenerativeReturn[TProperties]]
GroupByReturn: TypeAlias = Union[_GroupByReturn[Properties], _GroupByReturn[TProperties]]

ReturnProperties: TypeAlias = Union[PROPERTIES, Type[TProperties]]

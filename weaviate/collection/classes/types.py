from typing import Any, Dict, Mapping
from typing_extensions import TypeVar

Properties = TypeVar("Properties", bound=Mapping[str, Any], default=Dict[str, Any])
"""`Properties` is used wherever a single generic type is needed"""

TProperties = TypeVar("TProperties", bound=Mapping[str, Any], default=Dict[str, Any])
"""`TProperties` is used alongside `Properties` wherever there are two generic types needed

E.g., in `_DataCollection`, `Properties` is used when defining the generic of the class while
`TProperties` is used when defining the generic to be supplied in `.with_data_model` to create
a new instance of `_DataCollection` with a different `Properties` type.

To be clear: `_DataCollection[Properties]().with_data_model(TProperties) -> _DataCollection[TProperties]()`
"""

P = TypeVar("P")
"""`P` is a completely general type that is used wherever generic objects are defined that can be used
within the non-ORM and ORM APIs interchangeably"""

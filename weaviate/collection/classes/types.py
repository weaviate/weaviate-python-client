from typing import Any, Dict, Mapping
from typing_extensions import TypeVar

Properties = TypeVar("Properties", bound=Mapping[str, Any], default=Dict[str, Any])
TProperties = TypeVar("TProperties", bound=Mapping[str, Any], default=Dict[str, Any])

P = TypeVar("P")

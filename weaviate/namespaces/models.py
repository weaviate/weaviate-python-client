from dataclasses import dataclass
from typing import Literal, Optional

NamespaceState = Literal["active", "deleting"]


@dataclass
class Namespace:
    name: str
    home_node: Optional[str] = None
    state: Optional[NamespaceState] = None

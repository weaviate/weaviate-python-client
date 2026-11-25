from dataclasses import dataclass, field
from typing import List, Literal, Optional

NamespaceState = Literal["active", "suspended", "resuming", "deleting"]


@dataclass
class Namespace:
    name: str
    home_nodes: List[str] = field(default_factory=list)
    state: Optional[NamespaceState] = None

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class _BatchDeleteResult:
    failed: int
    matches: int
    objects: Optional[List[Dict[str, Any]]]
    successful: int

from dataclasses import dataclass
from typing import List, TypeAlias


@dataclass
class Error:
    code: int
    message: str


Errors: TypeAlias = List[Error]

from dataclasses import dataclass
from typing import List


@dataclass
class Error:
    code: int
    message: str


Errors = List[Error]

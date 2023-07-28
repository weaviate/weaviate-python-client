import uuid as uuid_package
from typing import Union, List, TypeAlias

UUID: TypeAlias = Union[str, uuid_package.UUID]
UUIDS: TypeAlias = Union[List[UUID], UUID]
NUMBERS: TypeAlias = Union[int, float]

BEACON = "weaviate://localhost/"

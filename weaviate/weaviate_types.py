import uuid as uuid_package
from typing import Union, List, TypeAlias, Tuple

UUID: TypeAlias = Union[str, uuid_package.UUID]
UUIDS: TypeAlias = Union[List[UUID], UUID]
NUMBER: TypeAlias = Union[int, float]
GEO_COORDINATES = Tuple[float, float]

BEACON = "weaviate://localhost/"

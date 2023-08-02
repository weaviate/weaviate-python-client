from typing import Union, List, Tuple

import uuid as uuid_package

UUID = Union[str, uuid_package.UUID]
UUIDS = Union[List[UUID], UUID]
NUMBER = Union[int, float]
GEO_COORDINATES = Tuple[float, float]

BEACON = "weaviate://localhost/"

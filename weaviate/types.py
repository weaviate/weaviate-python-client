import datetime
import uuid as uuid_package
from typing import Dict, Union, List, Sequence, Tuple

DATE = datetime.datetime
UUID = Union[str, uuid_package.UUID]
UUIDS = Union[Sequence[UUID], UUID]
NUMBER = Union[int, float]
GEO_COORDINATES = Tuple[float, float]
VECTORS = Union[Dict[str, List[float]], List[float]]
INCLUDE_VECTOR = Union[bool, str, List[str]]

BEACON = "weaviate://localhost/"

PRIMITIVE = Union[str, int, float, bool, datetime.datetime, uuid_package.UUID]

DATATYPE_TO_PYTHON_TYPE = {
    "text": str,
    "int": int,
    "text[]": List[str],
    "int[]": List[int],
    "boolean": bool,
    "boolean[]": List[bool],
    "number": float,
    "number[]": List[float],
    "date": datetime.datetime,
    "date[]": List[datetime.datetime],
    "geoCoordinates": GEO_COORDINATES,
    "object": Dict[str, PRIMITIVE],
    "object[]": List[Dict[str, PRIMITIVE]],
}
PYTHON_TYPE_TO_DATATYPE = {val: key for key, val in DATATYPE_TO_PYTHON_TYPE.items()}
TIME = datetime.datetime

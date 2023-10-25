import datetime
import uuid as uuid_package
from typing import Dict, Union, List, Tuple

UUID = Union[str, uuid_package.UUID]
UUIDS = Union[List[UUID], UUID]
NUMBER = Union[int, float]
GEO_COORDINATES = Tuple[float, float]

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

WeaviateField = Union[str, bool, int, float, UUID, GEO_COORDINATES, List["WeaviateField"]]

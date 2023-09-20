import datetime
import uuid as uuid_package
from typing import Union, List, Tuple

UUID = Union[str, uuid_package.UUID]
UUIDS = Union[List[UUID], UUID]
NUMBER = Union[int, float]
GEO_COORDINATES = Tuple[float, float]

BEACON = "weaviate://localhost/"

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
}
PYTHON_TYPE_TO_DATATYPE = {val: key for key, val in DATATYPE_TO_PYTHON_TYPE.items()}
TIME = datetime.datetime  # add datetime.date later

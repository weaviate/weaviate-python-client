import datetime
import uuid as uuid_package
from io import BufferedReader
from pathlib import Path
from typing import Mapping, Sequence

DATE = datetime.datetime
UUID = str | uuid_package.UUID
UUIDS = Sequence[UUID] | UUID
NUMBER = int | float
GEO_COORDINATES = tuple[float, float]
VECTORS = Mapping[str, Sequence[NUMBER] | Sequence[Sequence[NUMBER]]] | Sequence[NUMBER]
INCLUDE_VECTOR = bool | str | list[str]
BLOB_INPUT = str | Path | BufferedReader

BEACON = "weaviate://localhost/"

PRIMITIVE = str | int | float | bool | datetime.datetime | uuid_package.UUID

DATATYPE_TO_PYTHON_TYPE = {
    "text": str,
    "int": int,
    "text[]": list[str],
    "int[]": list[int],
    "boolean": bool,
    "boolean[]": list[bool],
    "number": float,
    "number[]": list[float],
    "date": datetime.datetime,
    "date[]": list[datetime.datetime],
    "geoCoordinates": GEO_COORDINATES,
    "object": dict[str, PRIMITIVE],
    "object[]": list[dict[str, PRIMITIVE]],
}
PYTHON_TYPE_TO_DATATYPE = {val: key for key, val in DATATYPE_TO_PYTHON_TYPE.items()}
TIME = datetime.datetime

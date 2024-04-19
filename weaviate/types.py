import datetime
import uuid as uuid_package
from typing import Dict, Union, List, Sequence, Tuple, Any, Annotated

import numpy
import numpy as np
from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema


class NdarrayModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """
        We return a pydantic_core.CoreSchema that behaves in the following ways:
        * `np.ndarray` will be parsed as `NdarrayModel` instances
        * `NdarrayModel` instances will be parsed as `NdarrayModel` instances without any changes
        """

        def validate_from_list(value: list) -> np.ndarray:
            return np.array(value)

        from_list_schema = core_schema.chain_schema(
            [
                core_schema.list_schema(),
                core_schema.no_info_plain_validator_function(validate_from_list),
            ]
        )

        return core_schema.json_or_python_schema(
            json_schema=from_list_schema,
            python_schema=core_schema.union_schema(
                [
                    core_schema.is_instance_schema(numpy.ndarray),
                    from_list_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: instance.squeeze().tolist()
            ),
        )


NdArrayType = Annotated[numpy.ndarray, NdarrayModel]

DATE = datetime.datetime
UUID = Union[str, uuid_package.UUID]
UUIDS = Union[Sequence[UUID], UUID]
NUMBER = Union[int, float]
GEO_COORDINATES = Tuple[float, float]
VECTORS = Union[Dict[str, List[float]], List[float], NdArrayType]
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

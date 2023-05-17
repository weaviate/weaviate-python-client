from typing import Dict, Any

import pytest as pytest

from weaviate.types import Class, Property, DataType


@pytest.mark.parametrize(
    "schema_class, expected",
    [
        (Class(name="ClassName"), {"class": "ClassName"}),
        (
            Class(
                name="ClassName",
                properties=[
                    Property(name="Prop1", dataType=DataType.UUID),
                    Property(name="Prop2", dataType=DataType.TEXT_ARRAY),
                ],
            ),
            {
                "class": "ClassName",
                "properties": [
                    {"name": "Prop1", "dataType": ["uuid"]},
                    {"name": "Prop2", "dataType": ["text[]"]},
                ],
            },
        ),
    ],
)
def test_schema_dataclass(schema_class: Class, expected: Dict[str, Any]):
    assert schema_class.to_dict() == expected

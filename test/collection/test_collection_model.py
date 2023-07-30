from typing import List

import pytest as pytest

from weaviate.collection.collection_model import BaseProperty


@pytest.mark.parametrize(
    "member_type,expected",
    [
        (str, "text"),
        (int, "int"),
        (float, "number"),
        (List[str], "text[]"),
        (List[int], "int[]"),
        (List[float], "number[]"),
    ],
)
def test_types(member_type, expected):
    class ModelTypes(BaseProperty):
        name: member_type

    non_optional_types = ModelTypes.type_to_dict(ModelTypes)
    assert non_optional_types[0]["dataType"][0] == expected

from typing import Any, Dict, Optional

import pytest as pytest

import weaviate
from weaviate import Config

CLASS1 = {
    "class": "Test",
    "properties": [
        {"name": "test", "dataType": ["string"]},
        {"name": "abc", "dataType": ["int"]},
    ],
}

CLASS2 = {
    "class": "Test2",
    "properties": [
        {"name": "test", "dataType": ["string"]},
        {"name": "abc", "dataType": ["int"]},
        {"name": "ref", "dataType": ["Test"]},
    ],
}
VECTOR = [1, 2, 3] * 100  # match with vectorizer vector length


UUID1 = "577887c1-4c6b-5594-aa62-f0c17883d9bf"
UUID2 = "577887c1-4c6b-5594-aa62-f0c17883d9cf"


@pytest.mark.parametrize("grpc_port", [50051, None])
@pytest.mark.parametrize("with_limit", [True, False])
@pytest.mark.parametrize("additional_props", [None, "id", ["id"], ["id", "vector"]])
@pytest.mark.parametrize(
    "near",
    [
        {"vector": VECTOR, "certainty": 0.5},
        {"vector": VECTOR, "distance": 0.5},
        {"vector": VECTOR},
        {"id": UUID2},
        {"id": UUID2, "certainty": 0.5},
        {"id": UUID2, "distance": 0.5},
    ],
)
@pytest.mark.parametrize(
    "properties",
    [
        "test",
        ["test", "abc"],
        ["test", "_additional{id}"],
        ["test", "ref {... on Test {test abc _additional{id vector}}}"],
    ],
)
def test_grcp(
    with_limit: bool, additional_props, near: Dict[str, Any], properties, grpc_port: Optional[int]
):

    client = weaviate.Client(
        "http://localhost:8080",
        additional_config=Config(grpc_port_experimental=grpc_port),
    )
    client.schema.delete_all()

    client.schema.create_class(CLASS1)
    client.schema.create_class(CLASS2)

    # add objects and references
    client.data_object.create({"test": "test1"}, "Test", vector=VECTOR)
    client.data_object.create({"test": "test2", "abc": 5}, "Test", vector=VECTOR, uuid=UUID1)
    client.data_object.create({"test": "test2", "abc": 5}, "Test2", vector=VECTOR, uuid=UUID2)
    client.data_object.reference.add(
        from_uuid=UUID2,
        to_uuid=UUID1,
        from_class_name="Test2",
        to_class_name="Test",
        from_property_name="ref",
    )

    query = client.query.get("Test2", properties)

    if with_limit:
        query.with_limit(10)

    if additional_props is not None:
        query.with_additional(additional_props)

    if "vector" in near:
        query.with_near_vector(near)
    if "id" in near:
        query.with_near_object(near)
    if "concepts" in near:
        query.with_near_text(near)

    result = query.do()
    assert "Test2" in result["data"]["Get"]
    assert "test" in result["data"]["Get"]["Test2"][0]

from typing import Any, Dict, Optional

import pytest as pytest

import weaviate

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
VECTOR = [1.5, 2.5, 3.5] * 100  # match with vectorizer vector length


UUID1 = "577887c1-4c6b-5594-aa62-f0c17883d9bf"
UUID2 = "577887c1-4c6b-5594-aa62-f0c17883d9cf"


@pytest.mark.parametrize("grpc_port", [50051, None])
@pytest.mark.parametrize("with_limit", [True, False])
@pytest.mark.parametrize("additional_props", [None, "id", ["id"], ["id", "vector"]])
@pytest.mark.parametrize(
    "search",
    [
        {"vector": VECTOR, "certainty": 0.5},
        {"vector": VECTOR, "distance": 0.5},
        {"vector": VECTOR},
        {"id": UUID2},
        {"id": UUID2, "certainty": 0.5},
        {"id": UUID2, "distance": 0.5},
        {"bm25": ""},
        {"hybrid": ""},
    ],
)
@pytest.mark.parametrize(
    "properties",
    [
        "test",
        ["test", "abc"],
        ["test", "ref {... on Test {test abc _additional{id vector}}}"],
    ],
)
def test_grcp(
    with_limit: bool, additional_props, search: Dict[str, Any], properties, grpc_port: Optional[int]
):
    client = weaviate.Client(
        "http://localhost:8080", additional_config=weaviate.Config(grpc_port_experimental=grpc_port)
    )
    client.schema.delete_all()

    client.schema.create_class(CLASS1)
    client.schema.create_class(CLASS2)

    # add objects and references
    client.data_object.create({"test": "test"}, "Test", vector=VECTOR)
    client.data_object.create({"test": "test", "abc": 5}, "Test", vector=VECTOR, uuid=UUID1)
    client.data_object.create({"test": "test", "abc": 5}, "Test2", vector=VECTOR, uuid=UUID2)
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

    if "vector" in search:
        query.with_near_vector(search)
    elif "id" in search:
        query.with_near_object(search)
    elif "concepts" in search:
        query.with_near_text(search)
    elif "bm25" in search:
        query.with_bm25(query="test", properties=["test"])
    elif "hybrid" in search:
        query.with_hybrid(query="test", properties=["test"], alpha=0.5, vector=VECTOR)

    result = query.do()
    assert "Test2" in result["data"]["Get"]
    assert "test" in result["data"]["Get"]["Test2"][0]


def test_additional():
    client_grpc = weaviate.Client(
        "http://localhost:8080", additional_config=weaviate.Config(grpc_port_experimental=50051)
    )
    client_grpc.schema.delete_all()

    client_grpc.schema.create_class(CLASS1)
    client_grpc.data_object.create({"test": "test"}, "Test", vector=VECTOR)
    client_gql = weaviate.Client(
        "http://localhost:8080", additional_config=weaviate.Config(grpc_port_experimental=50052)
    )

    results = []
    for client in [client_gql, client_grpc]:
        query = client.query.get("Test").with_additional(
            weaviate.AdditionalProperties(
                uuid=True,
                vector=True,
                creationTimeUnix=True,
                lastUpdateTimeUnix=True,
                distance=True,
            )
        )
        result = query.do()
        assert "Test" in result["data"]["Get"]

        results.append(result)

    result_gql = results[0]["data"]["Get"]["Test"][0]["_additional"]
    result_grpc = results[1]["data"]["Get"]["Test"][0]["_additional"]

    assert sorted(result_gql.keys()) == sorted(result_grpc.keys())
    for key in result_gql.keys():
        assert result_gql[key] == result_grpc[key]


def test_grpc_errors():
    client = weaviate.Client(
        "http://localhost:8080", additional_config=weaviate.Config(grpc_port_experimental=50051)
    )
    classname = CLASS1["class"]
    if client.schema.exists(classname):
        client.schema.delete_class(classname)
    client.schema.create_class(CLASS1)

    client.data_object.create({"test": "test"}, classname)

    # class errors
    res = client.query.get(classname + "does_not_exist", ["test"]).do()
    assert "errors" in res
    assert "data" not in res

    # prop errors
    res = client.query.get(classname, ["test", "made_up_prop"]).do()
    assert "errors" in res
    assert "data" not in res

import pytest

import weaviate

schema = {
    "classes": [
        {
            "class": "Ship",
            "description": "object",
            "properties": [
                {"dataType": ["string"], "description": "name", "name": "name"},
                {"dataType": ["string"], "description": "description", "name": "description"},
                {"dataType": ["int"], "description": "size", "name": "size"},
            ],
        }
    ]
}


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.create(schema)
    with client.batch as batch:
        batch.add_data_object(
            {"name": "HMS British Name", "size": 5, "description": "Super long description"}, "Ship"
        )
        batch.add_data_object(
            {
                "name": "The dragon ship",
                "size": 20,
                "description": "Interesting things about dragons",
            },
            "Ship",
        )
        batch.add_data_object(
            {"name": "Blackbeard", "size": 43, "description": "Background info about movies"},
            "Ship",
        )
        batch.add_data_object(
            {"name": "Titanic", "size": 1, "description": "Everyone knows"}, "Ship"
        )
        batch.add_data_object(
            {"name": "Artemis", "size": 34, "description": "Name from some story"}, "Ship"
        )
        batch.add_data_object(
            {"name": "The Crusty Crab", "size": 303, "description": "sponges, sponges, sponges"},
            "Ship",
        )
        batch.flush()

    yield client
    client.schema.delete_all()


def test_get_data(client):
    """Test GraphQL's Get clause."""
    where_filter = {"path": ["size"], "operator": "LessThan", "valueInt": 10}
    result = client.query.get("Ship", ["name", "size"]).with_limit(2).with_where(where_filter).do()
    objects = get_objects_from_result(result)
    a_found = False
    d_found = False
    for obj in objects:
        if obj["name"] == "HMS British Name":
            a_found = True
        if obj["name"] == "Titanic":
            d_found = True
    assert a_found and d_found and len(objects) == 2


def test_aggregate_data(client):
    """Test GraphQL's Aggregate clause."""
    where_filter = {"path": ["name"], "operator": "Equal", "valueString": "The dragon ship"}

    result = (
        client.query.aggregate("Ship")
        .with_where(where_filter)
        .with_group_by_filter(["name"])
        .with_fields("groupedBy {value}")
        .with_fields("name{count}")
        .do()
    )

    aggregation = get_aggregation_from_aggregate_result(result)
    assert "groupedBy" in aggregation, "Missing groupedBy"
    assert "name" in aggregation, "Missing name property"


def get_objects_from_result(result):
    return result["data"]["Get"]["Ship"]


def get_aggregation_from_aggregate_result(result):
    return result["data"]["Aggregate"]["Ship"][0]


def test_bm25(client):
    result = client.query.get("Ship", ["name"]).with_bm25("sponges", ["name", "description"]).do()
    assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"


def test_bm25_no_result(client):
    result = client.query.get("Ship", ["name"]).with_bm25("sponges", ["name"]).do()
    assert len(result["data"]["Get"]["Ship"]) == 0

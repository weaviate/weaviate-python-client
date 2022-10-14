import pytest

import weaviate
import time

schema = {
    "classes": [
        {
            "class": "Ship",
            "description": "object",
            "properties": [
                {
                    "dataType": [
                        "string"
                    ],
                    "description": "name",
                    "name": "name"
                },
                {
                    "dataType": [
                        "int"
                    ],
                    "description": "size",
                    "name": "size"
                }
            ]
        }
    ]
}


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.create(schema)
    client.data_object.create({"name": "A", "size": 5}, "Ship")
    client.data_object.create({"name": "B", "size": 20}, "Ship")
    client.data_object.create({"name": "C", "size": 43}, "Ship")
    client.data_object.create({"name": "D", "size": 1}, "Ship")
    client.data_object.create({"name": "E", "size": 34}, "Ship")
    client.data_object.create({"name": "F", "size": 303}, "Ship")
    time.sleep(2.0)

    yield client
    for _, cls in enumerate(schema["classes"]):
        client.schema.delete_class(cls["class"])


def test_get_data(client):
    """Test GraphQL's Get clause."""
    where_filter = {
        "path": ["size"],
        "operator":  "LessThan",
        "valueInt": 10
    }
    result = client.query\
        .get("Ship", ["name", "size"])\
        .with_limit(2)\
        .with_where(where_filter)\
        .do()
    objects = get_objects_from_result(result)
    a_found = False
    d_found = False
    for obj in objects:
        if obj["name"] == "A":
            a_found = True
        if obj["name"] == "D":
            d_found = True
    assert a_found and d_found and len(objects) == 2

def test_aggregate_data(client):
    """Test GraphQL's Aggregate clause."""
    where_filter = {
        "path": ["name"],
        "operator": "Equal",
        "valueString": "B"
    }

    result = client.query\
        .aggregate("Ship") \
        .with_where(where_filter) \
        .with_group_by_filter(["name"]) \
        .with_fields("groupedBy {value}") \
        .with_fields("name{count}") \
        .do()

    aggregation = get_aggregation_from_aggregate_result(result)
    assert "groupedBy" in aggregation, "Missing groupedBy"
    assert "name" in aggregation, "Missing name property"

def get_objects_from_result(result):
    return result["data"]["Get"]["Ship"]


def get_aggregation_from_aggregate_result(result):
    return result["data"]["Aggregate"]["Ship"][0]

import pytest

import weaviate


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    yield client
    client.schema.delete_all()


def test_create_class_with_explicit_replication_factor(client):
    single_class = {
        "class": "Barbecue",
        "description": "Barbecue or BBQ where meat and vegetables get grilled",
        "properties": [
            {
                "dataType": ["string"],
                "description": "how hot is the BBQ in C",
                "name": "heat",
            },
        ],
        "replicationConfig": {
            "factor": 2,
        },
    }
    client.schema.create_class(single_class)
    created_class = client.schema.get("Barbecue")
    assert created_class["class"] == "Barbecue"
    assert created_class["replicationConfig"]["factor"] == 2

    client.schema.delete_class("Barbecue")


def test_create_class_with_implicit_replication_factor(client):
    single_class = {
        "class": "Barbecue",
        "description": "Barbecue or BBQ where meat and vegetables get grilled",
        "properties": [
            {
                "dataType": ["string"],
                "description": "how hot is the BBQ in C",
                "name": "heat",
            },
        ],
    }
    client.schema.create_class(single_class)
    created_class = client.schema.get("Barbecue")
    assert created_class["class"] == "Barbecue"
    assert created_class["replicationConfig"]["factor"] == 1

    client.schema.delete_class("Barbecue")

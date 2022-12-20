from typing import Optional
import pytest

import weaviate


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("replicationFactor", [None, 2])
def test_create_class_with_implicit_and_explicit_replication_factor(
    client, replicationFactor: Optional[int]
):
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
    if replicationFactor is None:
        expectedFactor = 1
    else:
        expectedFactor = replicationFactor
        single_class["replicationConfig"] = {
            "factor": replicationFactor,
        }

    client.schema.create_class(single_class)
    created_class = client.schema.get("Barbecue")
    assert created_class["class"] == "Barbecue"
    assert created_class["replicationConfig"]["factor"] == expectedFactor

    client.schema.delete_class("Barbecue")

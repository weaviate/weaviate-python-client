from typing import Optional

import pytest

import weaviate
from weaviate.types import Property, Class, DataType


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("replicationFactor", [None, 1])
def test_create_class_with_implicit_and_explicit_replication_factor(
    client: weaviate.Client, replicationFactor: Optional[int]
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
        expected_factor = 1
    else:
        expected_factor = replicationFactor
        single_class["replicationConfig"] = {
            "factor": replicationFactor,
        }

    client.schema.create_class(single_class)
    created_class = client.schema.get("Barbecue")
    assert created_class["class"] == "Barbecue"
    assert created_class["replicationConfig"]["factor"] == expected_factor

    client.schema.delete_class("Barbecue")


@pytest.mark.parametrize("data_type", ["uuid", "uuid[]"])
def test_uuid_datatype(client, data_type):
    single_class = {"class": "UuidTest", "properties": [{"dataType": [data_type], "name": "heat"}]}

    client.schema.create_class(single_class)
    created_class = client.schema.get("uuidTest")
    assert created_class["class"] == "UuidTest"

    client.schema.delete_class("UuidTest")


@pytest.mark.parametrize("tokenization", ["word", "whitespace", "lowercase", "field"])
def test_tokenization(client, tokenization):
    single_class = {
        "class": "TokenTest",
        "properties": [{"dataType": ["text"], "name": "heat", "tokenization": tokenization}],
    }
    client.schema.create_class(single_class)
    created_class = client.schema.get("TokenTest")
    assert created_class["class"] == "TokenTest"

    client.schema.delete_class("TokenTest")


def test_class_exists(client: weaviate.Client):
    single_class = {"class": "Exists"}

    client.schema.create_class(single_class)
    assert client.schema.exists("Exists") is True
    assert client.schema.exists("DoesNotExists") is False

    client.schema.delete_class("Exists")
    assert client.schema.exists("Exists") is False


def test_schema_keys(client: weaviate.Client):
    single_class = {
        "class": "Author",
        "properties": [
            {
                "indexFilterable": False,
                "indexSearchable": False,
                "dataType": ["text"],
                "name": "name",
            }
        ],
    }
    client.schema.create_class(single_class)
    assert client.schema.exists("Author")


@pytest.mark.parametrize(
    "schema_class, expected",
    [
        (Class(name="testClass"), {"class": "TestClass"}),
        (
            Class(
                name="testClass",
                properties=[
                    Property(name="Prop1", dataType=DataType.UUID),
                    Property(name="Prop2", dataType=DataType.TEXT_ARRAY),
                ],
            ),
            {
                "class": "TestClass",
                "properties": [
                    {"name": "prop1", "dataType": ["uuid"]},
                    {"name": "prop2", "dataType": ["text[]"]},
                ],
            },
        ),
    ],
)
def test_dataclass_schema(client: weaviate.Client, schema_class, expected):
    if client.schema.exists(schema_class.name):
        client.schema.delete_class(schema_class.name)

    client.schema.create_class(schema_class)
    schema = client.schema.get(schema_class.name)

    for key, val in expected.items():
        assert key in schema
        if isinstance(val, dict):
            schema2 = schema[key]
            for key2 in val.keys():
                assert key2 in schema2
                assert schema[key2] == expected[key2]
        elif isinstance(val, list):
            for i in range(len(val)):
                schema2 = schema[key][i]
                for key2 in val[i].keys():
                    assert key2 in schema2
                    assert schema2[key2] == val[i][key2]
        else:
            assert schema[key] == expected[key]

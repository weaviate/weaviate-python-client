import os
import uuid

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

SHIPS = [
    {
        "props": {"name": "HMS British Name", "size": 5, "description": "Super long description"},
        "id": uuid.uuid4(),
    },
    {
        "props": {
            "name": "The dragon ship",
            "size": 20,
            "description": "Interesting things about dragons",
        },
        "id": uuid.uuid4(),
    },
    {
        "props": {"name": "Blackbeard", "size": 43, "description": "Background info about movies"},
        "id": uuid.uuid4(),
    },
    {"props": {"name": "Titanic", "size": 1, "description": "Everyone knows"}, "id": uuid.uuid4()},
    {
        "props": {"name": "Artemis", "size": 34, "description": "Name from some story"},
        "id": uuid.uuid4(),
    },
    {
        "props": {
            "name": "The Crusty Crab",
            "size": 303,
            "description": "sponges, sponges, sponges",
        },
        "id": uuid.uuid4(),
    },
]


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(schema)
    with client.batch as batch:
        for ship in SHIPS:

            batch.add_data_object(ship["props"], "Ship", ship["id"])

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


def test_get_data_after(client):
    full_results = client.query.get("Ship", ["name"]).with_additional(["id"]).do()
    for i, ship in enumerate(full_results["data"]["Get"]["Ship"][:-1]):
        result = (
            client.query.get("Ship", ["name"])
            .with_additional(["id"])
            .with_limit(1)
            .with_after(ship["_additional"]["id"])
            .do()
        )
        assert (
            result["data"]["Get"]["Ship"][0]["_additional"]["id"]
            == full_results["data"]["Get"]["Ship"][i + 1]["_additional"]["id"]
        )


def test_get_data_after_wrong_types(client):
    with pytest.raises(TypeError):
        client.query.get("Ship", ["name"]).with_additional(["id"]).with_limit(1).with_after(
            1234
        ).do()


def test_multi_get_data(client, people_schema):
    """Test GraphQL's MultiGet clause."""
    client.schema.create(people_schema)
    client.data_object.create(
        {
            "name": "John",
        },
        "Person",
    )
    result = client.query.multi_get(
        [
            client.query.get("Ship", ["name"])
            .with_alias("one")
            .with_sort({"path": ["name"], "order": "asc"}),
            client.query.get("Ship", ["size"])
            .with_alias("two")
            .with_sort({"path": ["size"], "order": "asc"}),
            client.query.get("Person", ["name"]),
        ]
    ).do()["data"]["Get"]
    assert result["one"][0]["name"] == "Artemis"
    assert result["two"][0]["size"] == 1
    assert result["Person"][0]["name"] == "John"


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
    assert len(result["data"]["Get"]["Ship"]) == 1
    assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"


def test_bm25_no_result(client):
    result = client.query.get("Ship", ["name"]).with_bm25("sponges", ["name"]).do()
    assert len(result["data"]["Get"]["Ship"]) == 0


def test_hybrid_bm25(client):
    """Test hybrid search with alpha=0.5 to have a combination of BM25 and vector search."""
    result = (
        client.query.get("Ship", ["name"]).with_hybrid("sponges", alpha=0.5, vector=[1] * 300).do()
    )

    # will find more results. "The Crusty Crab" is still first, because it matches with the BM25 search
    assert len(result["data"]["Get"]["Ship"]) >= 1
    assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"


@pytest.mark.parametrize(
    "single,grouped",
    [
        ("Describe the following as a Facebook Ad: {review}", None),
        (None, "Describe the following as a LinkedIn Ad: {review}"),
        (
            "Describe the following as a Twitter Ad: {review}",
            "Describe the following as a Mastodon Ad: {review}",
        ),
    ],
)
def test_generative_openai(single: str, grouped: str):
    """Test client credential flow with various providers."""
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    client = weaviate.Client(
        "http://127.0.0.1:8086", additional_headers={"X-OpenAI-Api-Key": api_key}
    )
    client.schema.delete_all()
    wine_class = {
        "class": "Wine",
        "properties": [
            {"name": "name", "dataType": ["string"]},
            {"name": "review", "dataType": ["string"]},
        ],
    }
    client.schema.create_class(wine_class)
    client.data_object.create(
        data_object={"name": "Super expensive wine", "review": "Tastes like a fresh ocean breeze"},
        class_name="Wine",
    )
    client.data_object.create(
        data_object={"name": "cheap wine", "review": "Tastes like forest"}, class_name="Wine"
    )

    result = (
        client.query.get("Wine", ["name", "review"])
        .with_generate(single_prompt=single, grouped_task=grouped)
        .do()
    )
    assert result["data"]["Get"]["Wine"][0]["_additional"]["generate"]["error"] is None

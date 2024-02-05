import json
import os
import uuid
from typing import Optional, List, Union

import pytest
from pytest import FixtureRequest

import weaviate
from weaviate import Tenant
from weaviate.data.replication import ConsistencyLevel
from weaviate.gql.get import HybridFusion

schema = {
    "classes": [
        {
            "class": "Ship",
            "description": "object",
            "properties": [
                {"dataType": ["string"], "description": "name", "name": "name"},
                {"dataType": ["string"], "description": "description", "name": "description"},
                {"dataType": ["int"], "description": "size", "name": "size"},
                {"dataType": ["number"], "description": "rating", "name": "rating"},
            ],
            "vectorizer": "text2vec-contextionary",
        }
    ]
}

SHIPS = [
    {
        "props": {
            "name": "HMS British Name",
            "size": 5,
            "rating": 0.0,
            "description": "Super long description",
        },
        "id": uuid.uuid4(),
    },
    {
        "props": {
            "name": "The dragon ship",
            "rating": 6.66,
            "size": 20,
            "description": "Interesting things about dragons",
        },
        "id": uuid.uuid4(),
    },
    {
        "props": {
            "name": "Blackbeard",
            "size": 43,
            "rating": 7.2,
            "description": "Background info about movies",
        },
        "id": uuid.uuid4(),
    },
    {
        "props": {"name": "Titanic", "size": 1, "rating": 4.5, "description": "Everyone knows"},
        "id": uuid.uuid4(),
    },
    {
        "props": {
            "name": "Artemis",
            "size": 34,
            "rating": 9.1,
            "description": "Name from some story",
        },
        "id": uuid.uuid4(),
    },
    {
        "props": {
            "name": "The Crusty Crab",
            "size": 303,
            "rating": 10.0,
            "description": "sponges, sponges, sponges",
        },
        "id": uuid.uuid4(),
    },
]


@pytest.fixture(scope="function")
def people_schema() -> str:
    with open(os.path.join(os.path.dirname(__file__), "people_schema.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def client(request):
    port = 8080
    opts = parse_client_options(request)
    if opts:
        if opts.get("cluster"):
            port = 8087
            for _, c in enumerate(schema["classes"]):
                c["replicationConfig"] = {"factor": 2}

    client = weaviate.Client(f"http://localhost:{port}")
    client.schema.delete_all()
    client.schema.create(schema)
    with client.batch as batch:
        for ship in SHIPS:
            batch.add_data_object(ship["props"], "Ship", ship["id"])

        batch.flush()

    yield client
    client.schema.delete_all()


def parse_client_options(request: FixtureRequest) -> dict:
    try:
        if isinstance(request.param, dict):
            return request.param
    except AttributeError:
        return


def test_get_data(client: weaviate.Client):
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


def test_get_data_with_where_contains_any(client: weaviate.Client):
    """Test GraphQL's Get clause with where filter."""
    where_filter = {"path": ["size"], "operator": "ContainsAny", "valueInt": [5]}
    result = client.query.get("Ship", ["name", "size"]).with_where(where_filter).do()
    objects = get_objects_from_result(result)
    assert len(objects) == 1 and objects[0]["name"] == "HMS British Name"


@pytest.mark.parametrize(
    "path,operator,value_type_key,value_type_value,name,expected_objects_len",
    [
        (
            ["description"],
            "ContainsAll",
            "valueString",
            ["sponges, sponges, sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAll",
            "valueText",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAll",
            "valueStringArray",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAll",
            "valueTextArray",
            ["sponges, sponges, sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAll",
            "valueStringList",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAll",
            "valueTextList",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAny",
            "valueString",
            ["sponges, sponges, sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAny",
            "valueText",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAny",
            "valueStringArray",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAny",
            "valueTextArray",
            ["sponges, sponges, sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAny",
            "valueStringList",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (
            ["description"],
            "ContainsAny",
            "valueTextList",
            ["sponges", "sponges", "sponges"],
            "The Crusty Crab",
            1,
        ),
        (["size"], "ContainsAll", "valueInt", [5], "HMS British Name", 1),
        (["size"], "ContainsAll", "valueIntList", [5], "HMS British Name", 1),
        (["size"], "ContainsAll", "valueIntArray", [5], "HMS British Name", 1),
        (["size"], "ContainsAny", "valueInt", [5], "HMS British Name", 1),
        (["size"], "ContainsAny", "valueIntList", [5], "HMS British Name", 1),
        (["size"], "ContainsAny", "valueIntArray", [5], "HMS British Name", 1),
        (["rating"], "ContainsAll", "valueNumber", [6.66], "The dragon ship", 1),
        (["rating"], "ContainsAll", "valueNumberList", [6.66], "The dragon ship", 1),
        (["rating"], "ContainsAll", "valueNumberArray", [6.66], "The dragon ship", 1),
        (["rating"], "ContainsAny", "valueNumber", [6.66], "The dragon ship", 1),
        (["rating"], "ContainsAny", "valueNumberList", [6.66], "The dragon ship", 1),
        (["rating"], "ContainsAny", "valueNumberArray", [6.66], "The dragon ship", 1),
        (["size"], "Equal", "valueInt", 5, "HMS British Name", 1),
        (["size"], "LessThan", "valueInt", 5, "Titanic", 1),
        (["size"], "LessThanEqual", "valueInt", 1, "Titanic", 1),
        (["size"], "GreaterThan", "valueInt", 300, "The Crusty Crab", 1),
        (["size"], "GreaterThanEqual", "valueInt", 303, "The Crusty Crab", 1),
        (["description"], "Like", "valueString", "sponges", "The Crusty Crab", 1),
        (["description"], "Like", "valueText", "sponges", "The Crusty Crab", 1),
        (["rating"], "IsNull", "valueBoolean", True, "irrelevant", 0),
        (["rating"], "NotEqual", "valueNumber", 6.66, "irrelevant", 5),
    ],
)
def test_get_data_with_where(
    client: weaviate.Client,
    path: List[str],
    operator: str,
    value_type_key: str,
    value_type_value: Union[List[int], List[str]],
    name,
    expected_objects_len: int,
):
    """Test GraphQL's Get clause with where filter."""
    where_filter = {
        "path": path,
        "operator": operator,
        value_type_key: value_type_value,
    }
    result = client.query.get("Ship", ["name"]).with_where(where_filter).do()
    objects = get_objects_from_result(result)
    if expected_objects_len == 0:
        assert objects is None
    else:
        assert len(objects) == expected_objects_len
        if expected_objects_len == 1:
            assert objects[0]["name"] == name


def test_get_data_after(client: weaviate.Client):
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


def test_get_data_after_wrong_types(client: weaviate.Client):
    with pytest.raises(TypeError):
        client.query.get("Ship", ["name"]).with_additional(["id"]).with_limit(1).with_after(
            1234
        ).do()


def test_multi_get_data(client: weaviate.Client, people_schema):
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


def test_aggregate_data(client: weaviate.Client):
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


def test_aggregate_data_with_group_by_and_limit(client: weaviate.Client):
    """Test GraphQL's Aggregate clause with group_by and limit."""
    result = (
        client.query.aggregate("Ship")
        .with_fields("name{count}")
        .with_limit(2)
        .with_group_by_filter(["name"])
        .do()
    )

    objects = get_objects_from_aggregate_result(result)
    assert len(objects) == 2, "Expected 2 results"


def test_aggregate_data_with_just_limit(client: weaviate.Client):
    """Test GraphQL's Aggregate clause with only limit. It's idempotent."""
    result = client.query.aggregate("Ship").with_fields("name{count}").with_limit(2).do()

    objects = get_objects_from_aggregate_result(result)
    assert objects == [
        {"name": {"count": len(SHIPS)}}
    ], f"Expected only meta count for {len(SHIPS)} results"


def get_objects_from_result(result):
    return result["data"]["Get"]["Ship"]


def get_aggregation_from_aggregate_result(result):
    return result["data"]["Aggregate"]["Ship"][0]


def get_objects_from_aggregate_result(result):
    return result["data"]["Aggregate"]["Ship"]


@pytest.mark.parametrize("query", ["sponges", "sponges\n"])
def test_bm25(client: weaviate.Client, query):
    result = client.query.get("Ship", ["name"]).with_bm25(query, ["name", "description"]).do()
    assert len(result["data"]["Get"]["Ship"]) == 1
    assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"


def test_bm25_no_result(client: weaviate.Client):
    result = client.query.get("Ship", ["name"]).with_bm25("sponges\n", ["name"]).do()
    assert len(result["data"]["Get"]["Ship"]) == 0


@pytest.mark.parametrize("query", ["sponges", "sponges\n"])
@pytest.mark.parametrize("fusion_type", [HybridFusion.RANKED, HybridFusion.RELATIVE_SCORE, None])
def test_hybrid(client: weaviate.Client, query: str, fusion_type: Optional[HybridFusion]):
    """Test hybrid search with alpha=0.5 to have a combination of BM25 and vector search."""
    result = (
        client.query.get("Ship", ["name", "description"])
        .with_hybrid(query, alpha=0.5, fusion_type=fusion_type)
        .do()
    )

    # will find more results. "The Crusty Crab" is still first, because it matches with the BM25 search
    assert len(result["data"]["Get"]["Ship"]) >= 1
    assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"


@pytest.mark.parametrize(
    "properties,num_results",
    [(None, 1), ([], 1), (["description"], 1), (["description", "name"], 1), (["name"], 0)],
)
def test_hybrid_properties(
    client: weaviate.Client, properties: Optional[List[str]], num_results: int
):
    """Test hybrid search with alpha=0.5 to have a combination of BM25 and vector search."""
    result = (
        client.query.get("Ship", ["name"])
        .with_hybrid("sponges", alpha=0.0, properties=properties)
        .do()
    )

    # "The Crusty Crab" has "sponges" in its description, it cannot be found in other properties
    if num_results > 0:
        assert len(result["data"]["Get"]["Ship"]) >= 1

        assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"
    else:
        assert len(result["data"]["Get"]["Ship"]) == 0


@pytest.mark.parametrize("autocut,num_results", [(1, 1), (2, 6), (-1, len(SHIPS))])
def test_autocut(client: weaviate.Client, autocut, num_results):
    result = (
        client.query.get("Ship", ["name"])
        .with_hybrid(query="sponges", properties=["name", "description"], alpha=0.5)
        .with_autocut(autocut)
        .with_limit(len(SHIPS))
        .do()
    )
    assert len(result["data"]["Get"]["Ship"]) == num_results
    assert result["data"]["Get"]["Ship"][0]["name"] == "The Crusty Crab"


def test_group_by(client: weaviate.Client, people_schema):
    """Test hybrid search with alpha=0.5 to have a combination of BM25 and vector search."""
    client.schema.delete_all()
    client.schema.create(people_schema)

    persons = []
    for i in range(10):
        persons.append(uuid.uuid4())
        client.data_object.create({"name": "randomName" + str(i)}, "Person", persons[-1])

    client.data_object.create({}, "Call", "3ab05e06-2bb2-41d1-b5c5-e044f3aa9623")
    client.data_object.create({}, "Call", "3ab05e06-2bb2-41d1-b5c5-e044f3aa9622")

    # create refs
    for i in range(5):
        client.data_object.reference.add(
            to_uuid=persons[i],
            from_property_name="caller",
            from_uuid="3ab05e06-2bb2-41d1-b5c5-e044f3aa9623"
            if i % 2 == 0
            else "3ab05e06-2bb2-41d1-b5c5-e044f3aa9622",
            from_class_name="Call",
            to_class_name="Person",
        )

    result = (
        client.query.get("Call", ["caller{... on Person{name}}"])
        .with_near_object({"id": "3ab05e06-2bb2-41d1-b5c5-e044f3aa9622"})
        .with_group_by(properties=["caller"], groups=2, objects_per_group=3)
        .with_additional("group{hits {_additional{vector}caller{... on Person{name}}}}")
        .do()
    )

    # will find more results. "The Crusty Crab" is still first, because it matches with the BM25 search
    assert len(result["data"]["Get"]["Call"]) >= 1
    # assert result["data"]["Get"]["Call"][0]["caller"][0]["name"] == "randomName0"


@pytest.mark.parametrize(
    "client,level",
    [
        ({"cluster": True}, ConsistencyLevel.ONE),
        ({"cluster": True}, ConsistencyLevel.QUORUM),
        ({"cluster": True}, ConsistencyLevel.ALL),
    ],
    indirect=["client"],
)
def test_consistency_level(client: weaviate.Client, level):
    result = (
        client.query.get("Ship", ["name"])
        .with_consistency_level(level)
        .with_additional("isConsistent")
        .do()
    )
    for _, res in enumerate(get_objects_from_result(result)):
        assert res["_additional"]["isConsistent"]


@pytest.mark.parametrize(
    "single,grouped",
    [
        ("Describe the following as a Facebook Ad: {review}", None),
        (None, "Describe the following as a LinkedIn Ad: {review}"),
        (
            "Describe the following as a Twitter Ad: {review}",
            "Describe the following as a Mastodon Ad: {review}",
        ),
        (
            "Describe the following as a Twitter Ad: \n Review: {review} \n Name: {name}",
            "Describe the following as a Mastodon Ad:  \n Review: {review} \n Name: {name}",
        ),
    ],
)
def test_generative_openai(single: str, grouped: str):
    """Test client credential flow with various providers."""
    api_key = os.environ.get("OPENAI_APIKEY")
    if api_key is None:
        pytest.skip("No OpenAI API key found.")

    client = weaviate.Client(
        "http://localhost:8086", additional_headers={"X-OpenAI-Api-Key": api_key}
    )
    client.schema.delete_all()
    wine_class = {
        "class": "Wine",
        "properties": [
            {"name": "name", "dataType": ["string"]},
            {"name": "review", "dataType": ["string"]},
        ],
        "moduleConfig": {"generative-openai": {}},
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

    grouped_properties = ["review"]
    result = (
        client.query.get("Wine", ["name", "review"])
        .with_generate(
            single_prompt=single, grouped_task=grouped, grouped_properties=grouped_properties
        )
        .do()
    )
    assert result["data"]["Get"]["Wine"][0]["_additional"]["generate"]["error"] is None


def test_graphql_with_tenant():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    schema_class = {
        "class": "GraphQlTenantClass",
        "vectorizer": "none",
        "multiTenancyConfig": {"enabled": True},
    }

    tenants = ["tenant1", "tenant2"]
    client.schema.create_class(schema_class)
    client.schema.add_class_tenants(schema_class["class"], [Tenant(tenant) for tenant in tenants])

    nr_objects = 101
    with client.batch() as batch:
        for i in range(nr_objects):
            batch.add_data_object(
                class_name=schema_class["class"], tenant=tenants[i % 2], data_object={}
            )

    # no results without tenant
    results = client.query.get(schema_class["class"]).with_additional("id").do()
    assert results["data"]["Get"][schema_class["class"]] is None
    assert results["errors"] is not None

    # get call with tenant only returns the objects for a given tenant
    results = (
        client.query.get(schema_class["class"]).with_additional("id").with_tenant(tenants[0]).do()
    )
    assert len(results["data"]["Get"][schema_class["class"]]) == nr_objects // 2 + 1

    results = (
        client.query.get(schema_class["class"]).with_additional("id").with_tenant(tenants[1]).do()
    )
    assert len(results["data"]["Get"][schema_class["class"]]) == nr_objects // 2

    results = client.query.aggregate(schema_class["class"]).with_meta_count().do()
    assert results["data"]["Aggregate"][schema_class["class"]] is None
    assert results["errors"] is not None

    results = (
        client.query.aggregate(schema_class["class"]).with_meta_count().with_tenant(tenants[0]).do()
    )
    assert (
        int(results["data"]["Aggregate"][schema_class["class"]][0]["meta"]["count"])
        == nr_objects // 2 + 1
    )

    results = (
        client.query.aggregate(schema_class["class"]).with_meta_count().with_tenant(tenants[1]).do()
    )
    assert (
        int(results["data"]["Aggregate"][schema_class["class"]][0]["meta"]["count"])
        == nr_objects // 2
    )


def test_graphql_with_nested_object():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create_class(
        {
            "class": "NestedObjectClass",
            "vectorizer": "none",
            "properties": [
                {
                    "name": "nested",
                    "dataType": ["object"],
                    "nestedProperties": [
                        {
                            "name": "name",
                            "dataType": ["text"],
                        },
                        {
                            "name": "names",
                            "dataType": ["text[]"],
                        },
                        {
                            "name": "age",
                            "dataType": ["int"],
                        },
                        {
                            "name": "ages",
                            "dataType": ["int[]"],
                        },
                        {
                            "name": "weight",
                            "dataType": ["number"],
                        },
                        {
                            "name": "weights",
                            "dataType": ["number[]"],
                        },
                        {
                            "name": "isAlive",
                            "dataType": ["boolean"],
                        },
                        {
                            "name": "areAlive",
                            "dataType": ["boolean[]"],
                        },
                        {
                            "name": "date",
                            "dataType": ["date"],
                        },
                        {
                            "name": "dates",
                            "dataType": ["date[]"],
                        },
                        {
                            "name": "uuid",
                            "dataType": ["uuid"],
                        },
                        {
                            "name": "uuids",
                            "dataType": ["uuid[]"],
                        },
                    ],
                }
            ],
        }
    )
    data = {
        "name": "nested object",
        "names": ["nested", "object"],
        "age": 42,
        "ages": [42, 43],
        "weight": 42.42,
        "weights": [42.42, 43.43],
        "isAlive": True,
        "areAlive": [True, False],
        "date": "2021-01-01T00:00:00Z",
        "dates": ["2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z"],
        "uuid": "00000000-0000-0000-0000-000000000000",
        "uuids": ["00000000-0000-0000-0000-000000000000", "00000000-0000-0000-0000-000000000001"],
    }
    uuid_ = client.data_object.create({"nested": data}, "NestedObjectClass")

    results = client.query.get(
        "NestedObjectClass",
        [
            "nested { name names age ages weight weights isAlive areAlive date dates uuid uuids } _additional { id }"
        ],
    ).do()
    print(results)
    assert results["data"]["Get"]["NestedObjectClass"][0]["nested"] == data
    assert results["data"]["Get"]["NestedObjectClass"][0]["_additional"]["id"] == uuid_

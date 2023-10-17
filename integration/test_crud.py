import json
import os
import time
from datetime import datetime
from datetime import timezone
from typing import List, Optional, Dict, Union

import pytest
import uuid

import weaviate
from weaviate import Tenant
from weaviate.gql.get import LinkTo


def get_query_for_group(name):
    return (
        """
    {
      Get {
        Group (where: {
          path: ["name"]
          operator: Equal
          valueText: "%s"
        }) {
          name
          _additional {
            id
          }
          members {
            ... on Person {
              name
              _additional {
                id
              }
            }
          }
        }
      }
    }
    """
        % name
    )


gql_get_sophie_scholl = """
{
  Get {
    Person (where: {
      path: ["id"]
      operator: Equal
      valueString: "594b7827-f795-40d0-aabb-5e0553953dad"
    }){
      name
      _additional {
        id
      }
    }
  }
}
"""

SHIP_SCHEMA = {
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
def people_schema() -> str:
    with open(os.path.join(os.path.dirname(__file__), "people_schema.json"), encoding="utf-8") as f:
        return json.load(f)


def test_load_scheme(people_schema):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(people_schema)

    assert client.schema.contains()
    assert client.schema.contains(people_schema)

    for cls in people_schema["classes"]:
        client.schema.delete_class(cls["class"])


@pytest.fixture(scope="module")
def client(people_schema):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(people_schema)

    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("timeout, error", [(None, TypeError), ((5,), ValueError)])
def test_timeout_error(timeout, error):
    with pytest.raises(error):
        weaviate.Client("http://localhost:8080", timeout_config=timeout)


@pytest.mark.parametrize("timeout", [(5, 5), 5, 5.0, (5.0, 5.0), (5, 5.0)])
def test_timeout(people_schema, timeout):
    client = weaviate.Client("http://localhost:8080", timeout_config=timeout)
    client.schema.delete_all()
    client.schema.create(people_schema)
    expected_name = "Sophie Scholl"
    client.data_object.create(
        {"name": expected_name}, "Person", "594b7827-f795-40d0-aabb-5e0553953dad"
    )
    time.sleep(0.5)
    result = client.query.raw(gql_get_sophie_scholl)
    assert result["data"]["Get"]["Person"][0]["name"] == expected_name
    client.schema.delete_all()


@pytest.mark.parametrize("limit", [None, 1, 5, 20, 50])
def test_query_get_with_limit(people_schema, limit: Optional[int]):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(people_schema)

    num_objects = 20
    for i in range(num_objects):
        with client.batch as batch:
            batch.add_data_object({"name": f"name{i}"}, "Person")
        batch.flush()
    result = client.data_object.get(class_name="Person", limit=limit)
    if limit is None or limit >= num_objects:
        assert len(result["objects"]) == num_objects
    else:
        assert len(result["objects"]) == limit
    client.schema.delete_all()


def test_query_get_with_after(people_schema):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(people_schema)

    num_objects = 20
    for i in range(num_objects):
        with client.batch as batch:
            batch.add_data_object({"name": f"name{i}"}, "Person")
        batch.flush()

    full_results = client.data_object.get(class_name="Person")
    for i, person in enumerate(full_results["objects"][:-1]):
        results = client.data_object.get(class_name="Person", limit=1, after=person["id"])
        assert full_results["objects"][i + 1]["id"] == results["objects"][0]["id"]

    client.schema.delete_all()


@pytest.mark.parametrize("offset", [None, 0, 1, 5, 20, 50])
def test_query_get_with_offset(people_schema, offset: Optional[int]):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(people_schema)

    num_objects = 20
    for i in range(num_objects):
        with client.batch as batch:
            batch.add_data_object({"name": f"name{i}"}, "Person")
        batch.flush()
    result_without_offset = client.data_object.get(class_name="Person")
    result_with_offset = client.data_object.get(class_name="Person", offset=offset)

    if offset is None:
        assert result_with_offset["objects"] == result_without_offset["objects"]
    elif offset >= num_objects:
        assert len(result_with_offset["objects"]) == 0
    else:
        assert result_with_offset["objects"][:] == result_without_offset["objects"][offset:]
    client.schema.delete_all()


@pytest.mark.parametrize(
    "sort,expected",
    [
        (
            {"properties": "name", "order_asc": True},
            ["name" + "{:02d}".format(i) for i in range(0, 20)],
        ),
        (
            {"properties": "name", "order_asc": False},
            ["name" + "{:02d}".format(i) for i in range(19, -1, -1)],
        ),
        (
            {"properties": ["name"], "order_asc": [False]},
            ["name" + "{:02d}".format(i) for i in range(19, -1, -1)],
        ),
        (
            {"properties": ["description", "size", "name"], "order_asc": [False, True, False]},
            ["name05", "name00", "name06", "name01"],
        ),
        (
            {"properties": ["description", "size", "name"], "order_asc": False},
            ["name09", "name04", "name08", "name03"],
        ),
        (
            {"properties": ["description", "size", "name"], "order_asc": True},
            ["name10", "name15", "name11", "name16"],
        ),
        ({"properties": ["description", "size", "name"]}, ["name10", "name15", "name11", "name16"]),
    ],
)
def test_query_get_with_sort(
    sort: Optional[Dict[str, Union[str, bool, List[bool], List[str]]]], expected: List[str]
):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(SHIP_SCHEMA)

    num_objects = 10
    for i in range(num_objects):
        with client.batch as batch:
            batch.add_data_object(
                {
                    "name": "name" + "{:02d}".format(i),
                    "size": i % 5 + 5,
                    "description": "Super long description",
                },
                "Ship",
            )
            batch.add_data_object(
                {
                    "name": "name" + "{:02d}".format(i + 10),
                    "size": i % 5 + 5,
                    "description": "Short description",
                },
                "Ship",
            )
        batch.flush()
    result = client.data_object.get(class_name="Ship", sort=sort)

    for i, exp in enumerate(expected):
        assert exp == result["objects"][i]["properties"]["name"]
    client.schema.delete_all()


def test_query_data(client: weaviate.Client):
    expected_name = "Sophie Scholl"
    client.data_object.create(
        {"name": expected_name}, "Person", "594b7827-f795-40d0-aabb-5e0553953dad"
    )
    time.sleep(2.0)
    result = client.query.raw(gql_get_sophie_scholl)
    assert result["data"]["Get"]["Person"][0]["name"] == expected_name


def test_create_schema():
    client = weaviate.Client("http://localhost:8080")
    single_class = {
        "class": "Barbecue",
        "description": "Barbecue or BBQ where meat and vegetables get grilled",
    }
    client.schema.create_class(single_class)
    prop = {
        "dataType": ["string"],
        "description": "how hot is the BBQ in C",
        "name": "heat",
    }
    client.schema.property.create("Barbecue", prop)
    classes = client.schema.get()["classes"]
    found = False
    for class_ in classes:
        if class_["class"] == "Barbecue":
            found = len(class_["properties"]) == 1
    assert found
    client.schema.delete_class("Barbecue")


def test_replace_and_update(client: weaviate.Client):
    """Test updating an object with put (replace) and patch (update)."""
    uuid = "28954264-0449-57a2-ade5-e9e08d11f51a"
    client.data_object.create({"name": "Someone"}, "Person", uuid)
    person = client.data_object.get_by_id(uuid, class_name="Person")
    assert person["properties"]["name"] == "Someone"
    client.data_object.replace({"name": "SomeoneElse"}, "Person", uuid)
    person = client.data_object.get_by_id(uuid, class_name="Person")
    assert person["properties"]["name"] == "SomeoneElse"
    client.data_object.update({"name": "Anyone"}, "Person", uuid)
    person = client.data_object.get_by_id(uuid, class_name="Person")
    assert person["properties"]["name"] == "Anyone"
    client.data_object.delete(uuid, class_name="Person")


def test_crud(client: weaviate.Client):
    chemists: List[str] = []
    _create_objects_batch(client)
    _create_objects(client, chemists)
    time.sleep(2.0)
    _create_references(client, chemists)
    time.sleep(2.0)
    _validate_data_loading(client)
    _delete_objects(client, chemists)

    _delete_references(client)
    _get_data(client)


def _create_objects_batch(local_client: weaviate.Client):
    local_client.batch.add_data_object({"name": "John Rawls"}, "Person")
    local_client.batch.add_data_object({"name": "Emanuel Kant"}, "Person")
    local_client.batch.add_data_object({"name": "Plato"}, "Person")
    local_client.batch.add_data_object({"name": "Pull-up"}, "Exercise")
    local_client.batch.add_data_object({"name": "Squat"}, "Exercise")
    local_client.batch.add_data_object({"name": "Star jump"}, "Exercise")

    local_client.batch.create_objects()


def _create_objects(local_client: weaviate.Client, chemists: List[str]):
    local_client.data_object.create(
        {"name": "Andrew S. Tanenbaum"}, "Person", "28954261-0449-57a2-ade5-e9e08d11f51a"
    )
    local_client.data_object.create(
        {"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446"
    )
    local_client.data_object.create(
        {"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642"
    )
    local_client.data_object.create(
        {"name": "Tim Berners-Lee"}, "Person", "d1e90d26-d82e-5ef8-84f6-ca67119c7998"
    )
    local_client.data_object.create(
        {"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6"
    )
    local_client.data_object.create(
        {"name": "Chemists"}, "Group", "577887c1-4c6b-5594-aa62-f0c17883d9bf"
    )

    for name in ["Marie Curie", "Fritz Haber", "Walter White"]:
        chemists.append(local_client.data_object.create({"name": name}, "Person"))

    local_time = datetime.now(timezone.utc).astimezone()
    local_client.data_object.create(
        {"start": local_time.isoformat()}, "Call", "3ab05e06-2bb2-41d1-b5c5-e044f3aa9623"
    )


def _create_references(local_client: weaviate.Client, chemists: List[str]):
    local_client.data_object.reference.add(
        "2db436b5-0557-5016-9c5f-531412adf9c6",
        "members",
        "b36268d4-a6b5-5274-985f-45f13ce0c642",
        from_class_name="Group",
        to_class_name="Person",
    )
    local_client.data_object.reference.add(
        "2db436b5-0557-5016-9c5f-531412adf9c6",
        "members",
        "1c9cd584-88fe-5010-83d0-017cb3fcb446",
        from_class_name="Group",
        to_class_name="Person",
    )

    for chemist in chemists:
        local_client.batch.add_reference(
            "577887c1-4c6b-5594-aa62-f0c17883d9bf",
            "Group",
            "members",
            chemist,
            to_object_class_name="Person",
        )

    local_client.batch.create_references()


def _validate_data_loading(local_client: weaviate.Client):
    legends = local_client.query.raw(get_query_for_group("Legends"))["data"]["Get"]
    for member in legends["Group"][0]["members"]:
        assert member["name"] in ["John von Neumann", "Alan Turing"]

    group_chemists = local_client.query.raw(get_query_for_group("Chemists"))["data"]["Get"]
    for member in group_chemists["Group"][0]["members"]:
        assert member["name"] in ["Marie Curie", "Fritz Haber", "Walter White"]
    assert len(group_chemists["Group"][0]["members"]) == 3


def _delete_objects(local_client: weaviate.Client, chemists: List[str]):
    local_client.data_object.delete(
        chemists[2], class_name="Person"
    )  # Delete Walter White not a real chemist just a legend
    time.sleep(1.1)
    assert not local_client.data_object.exists(
        chemists[2], class_name="Person"
    ), "Thing was not correctly deleted"


def _delete_references(local_client: weaviate.Client):
    # Test delete reference
    prime_ministers_group = local_client.data_object.create({"name": "Prime Ministers"}, "Group")
    prime_ministers = []
    for name in ["Wim Kok", "Dries van Agt", "Piet de Jong"]:
        prime_ministers.append(local_client.data_object.create({"name": name}, "Person"))
    for prime_minister in prime_ministers:
        local_client.data_object.reference.add(
            prime_ministers_group,
            "members",
            prime_minister,
            from_class_name="Group",
            to_class_name="Person",
        )
    time.sleep(2.0)
    local_client.data_object.reference.delete(
        prime_ministers_group,
        "members",
        prime_ministers[0],
        from_class_name="Group",
        to_class_name="Person",
    )
    time.sleep(2.0)
    prime_ministers_group_object = local_client.data_object.get_by_id(
        prime_ministers_group, class_name="Group"
    )
    assert (
        len(prime_ministers_group_object["properties"]["members"]) == 2
    ), "Reference not deleted correctly"


def _get_data(local_client: weaviate.Client):
    local_client.data_object.create(
        {"name": "George Floyd"}, "Person", "452e3031-bdaa-4468-9980-aed60d0258bf"
    )
    time.sleep(2.0)
    person = local_client.data_object.get_by_id(
        "452e3031-bdaa-4468-9980-aed60d0258bf",
        ["interpretation"],
        with_vector=True,
        class_name="Person",
    )
    assert "vector" in person
    assert (
        "interpretation" in person["additional"]
    ), "additional property _interpretation not in person"

    persons = local_client.data_object.get(with_vector=True)
    assert "vector" in persons["objects"][0], "additional property _vector not in persons"


def test_add_vector_and_vectorizer(client: weaviate.Client):
    """Add objects with and without vector.

    The Vectorizer should create a vector for the object without vector and the given one should be used for the object
    with vector.
    """
    uuid_without_vector = uuid.uuid4()
    uuid_with_vector = uuid.uuid4()
    with client.batch(batch_size=2) as batch:
        batch.add_data_object({"name": "Some Name"}, "Person", uuid=uuid_without_vector)
        batch.add_data_object(
            {"name": "Other Name"}, "Person", uuid=uuid_with_vector, vector=[1] * 300
        )
        batch.flush()

    object_with_vector = client.data_object.get_by_id(
        uuid_with_vector,
        with_vector=True,
        class_name="Person",
    )
    assert object_with_vector["vector"] == [1] * 300

    object_without_vector = client.data_object.get_by_id(
        uuid_without_vector,
        with_vector=True,
        class_name="Person",
    )
    assert object_without_vector["vector"] != [1] * 300


def test_beacon_refs(people_schema: dict):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create(people_schema)

    persons = []
    for i in range(10):
        persons.append(uuid.uuid4())
        client.data_object.create({"name": "randomName" + str(i)}, "Person", persons[-1])

    client.data_object.create({}, "Call", "3ab05e06-2bb2-41d1-b5c5-e044f3aa9623")

    # create refs
    for i in range(5):
        client.data_object.reference.add(
            to_uuid=persons[i],
            from_property_name="caller",
            from_uuid="3ab05e06-2bb2-41d1-b5c5-e044f3aa9623",
            from_class_name="Call",
            to_class_name="Person",
        )

    result = client.query.get(
        "Call",
        [
            "start",
            LinkTo(link_on="caller", linked_class="Person", properties=["name"]),
        ],
    ).do()
    callers = result["data"]["Get"]["Call"][0]["caller"]
    assert len(callers) == 5
    all_names = [caller["name"] for caller in callers]
    assert all("randomName" + str(i) in all_names for i in range(5))


def test_beacon_refs_multiple(people_schema: dict):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create_class(
        {
            "class": "Person",
            "description": "A person such as humans or personality known through culture",
            "properties": [
                {"name": "name", "dataType": ["string"]},
                {"name": "age", "dataType": ["int"]},
                {"name": "born_in", "dataType": ["text"]},
            ],
            "vectorizer": "none",
        }
    )

    client.schema.create_class(
        {
            "class": "Call",
            "description": "A call between two Persons",
            "properties": [
                {"name": "caller", "dataType": ["Person"]},
                {"name": "recipient", "dataType": ["Person"]},
            ],
            "vectorizer": "none",
        }
    )

    persons = []
    for i in range(10):
        persons.append(uuid.uuid4())
        client.data_object.create(
            {"name": "randomName" + str(i), "age": i, "born_in": "city" + str(i)},
            "Person",
            persons[-1],
        )

    call_uuids = [uuid.uuid4(), uuid.uuid4()]
    client.data_object.create({}, "Call", call_uuids[0])
    client.data_object.create({}, "Call", call_uuids[1])

    # create refs
    for i in range(4):
        client.data_object.reference.add(call_uuids[i % 2], "caller", persons[i], "Call", "Person")
        client.data_object.reference.add(
            call_uuids[i % 2], "recipient", persons[i + 5], "Call", "Person"
        )

    result = client.query.get(
        "Call",
        [
            LinkTo(link_on="caller", linked_class="Person", properties=["name", "age"]),
            LinkTo(link_on="recipient", linked_class="Person", properties=["born_in", "age"]),
        ],
    ).do()
    call1 = result["data"]["Get"]["Call"][0]
    call2 = result["data"]["Get"]["Call"][1]

    # each call has two callers and recipients and caller and recipient should contain different entries
    for call in [call1, call2]:
        assert len(call["caller"]) == 2
        assert len(call["recipient"]) == 2

        assert "age" in call["caller"][0] and "name" in call["caller"][0]
        assert "age" in call["recipient"][0] and "born_in" in call["recipient"][0]


def test_beacon_refs_nested():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create_class(
        {
            "class": "A",
            "properties": [{"name": "nonRef", "dataType": ["string"]}],
            "vectorizer": "none",
        }
    )
    client.schema.create_class(
        {
            "class": "B",
            "properties": [
                {"name": "nonRef", "dataType": ["string"]},
                {"name": "refA", "dataType": ["A"]},
            ],
            "vectorizer": "none",
        }
    )
    client.schema.create_class(
        {
            "class": "C",
            "properties": [
                {"name": "nonRef", "dataType": ["string"]},
                {"name": "refB", "dataType": ["B"]},
            ],
            "vectorizer": "none",
        }
    )
    client.schema.create_class(
        {
            "class": "D",
            "properties": [
                {"name": "nonRef", "dataType": ["string"]},
                {"name": "refC", "dataType": ["C"]},
                {"name": "refB", "dataType": ["B"]},
            ],
            "vectorizer": "none",
        }
    )

    uuid_a = client.data_object.create({"nonRef": "A"}, "A")
    uuid_b = client.data_object.create({"nonRef": "B"}, "B")
    client.data_object.reference.add(uuid_b, "refA", uuid_a, "B", "A")

    uuid_c = client.data_object.create({"nonRef": "C"}, "C")
    client.data_object.reference.add(uuid_c, "refB", uuid_b, "C", "B")

    uuid_d = client.data_object.create({"nonRef": "D"}, "D")
    client.data_object.reference.add(uuid_d, "refC", uuid_c, "D", "C")
    client.data_object.reference.add(uuid_d, "refB", uuid_b, "D", "B")

    result = client.query.get(
        "D",
        [
            "nonRef",
            LinkTo(
                link_on="refC",
                linked_class="C",
                properties=[
                    "nonRef",
                    LinkTo(
                        link_on="refB",
                        linked_class="B",
                        properties=[
                            "nonRef",
                            LinkTo(link_on="refA", linked_class="A", properties=["nonRef"]),
                        ],
                    ),
                ],
            ),
            LinkTo(
                link_on="refB",
                linked_class="B",
                properties=[
                    "nonRef",
                    LinkTo(link_on="refA", linked_class="A", properties=["nonRef"]),
                ],
            ),
        ],
    ).do()

    assert result["data"]["Get"]["D"][0]["refC"][0]["refB"][0]["refA"][0]["nonRef"] == "A"
    assert result["data"]["Get"]["D"][0]["refB"][0]["refA"][0]["nonRef"] == "A"


def test_tenants():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    tenants = [
        Tenant(name="tenantA"),
        Tenant(name="tenantB"),
        Tenant(name="tenantC"),
    ]

    class_name_document = "Document"
    client.schema.create_class(
        {
            "class": class_name_document,
            "properties": [
                {"name": "tenant", "dataType": ["text"]},
                {"name": "title", "dataType": ["text"]},
            ],
            "vectorizer": "none",
            "multiTenancyConfig": {"enabled": True},
        }
    )
    client.schema.add_class_tenants(
        class_name=class_name_document,
        tenants=tenants,
    )
    document_uuids = [
        "00000000-0000-0000-0000-000000000011",
        "00000000-0000-0000-0000-000000000022",
        "00000000-0000-0000-0000-000000000033",
    ]
    document_titles = ["GAN", "OpenAI", "SpaceX"]
    for i in range(0, len(document_uuids)):
        client.data_object.create(
            class_name=class_name_document,
            uuid=document_uuids[i],
            data_object={
                "tenant": tenants[i].name,
                "title": document_titles[i],
            },
            tenant=tenants[i].name,
        )
    documents = client.data_object.get(class_name=class_name_document, tenant=tenants[0].name)
    assert len(documents["objects"]) == 1

    class_name_passage = "Passage"
    client.schema.create_class(
        {
            "class": class_name_passage,
            "properties": [
                {"name": "tenant", "dataType": ["text"]},
                {"name": "content", "dataType": ["text"]},
                {"name": "ofDocument", "dataType": ["Document"]},
            ],
            "vectorizer": "none",
            "multiTenancyConfig": {"enabled": True},
        }
    )
    client.schema.add_class_tenants(
        class_name=class_name_passage,
        tenants=tenants,
    )

    passage_uuids = [
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "00000000-0000-0000-0000-000000000003",
    ]
    txts = ["Txt1", "Txt2", "Txt3"]

    for i in range(0, len(passage_uuids)):
        client.data_object.create(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            data_object={
                "content": txts[i],
                "tenant": tenants[i].name,
            },
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        passage = client.data_object.get_by_id(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert passage["properties"]["tenant"] == tenants[i].name
        assert passage["properties"]["content"] == txts[i]
    passages = client.data_object.get(class_name=class_name_passage, tenant=tenants[0].name)
    assert len(passages["objects"]) == 1

    for i in range(0, len(passage_uuids)):
        client.data_object.replace(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            data_object={
                "content": txts[len(txts) - i - 1],
                "tenant": tenants[i].name,
            },
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        exists = client.data_object.exists(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert exists
        passage = client.data_object.get_by_id(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert passage["properties"]["tenant"] == tenants[i].name
        assert passage["properties"]["content"] == txts[len(txts) - i - 1]

    for i in range(0, len(passage_uuids)):
        client.data_object.update(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            data_object={
                "content": tenants[i].name,
            },
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        passage = client.data_object.get_by_id(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert passage["properties"]["tenant"] == tenants[i].name
        assert passage["properties"]["content"] == tenants[i].name

    # references
    for i in range(0, len(passage_uuids)):
        client.data_object.reference.add(
            passage_uuids[i],
            "ofDocument",
            document_uuids[i],
            from_class_name="Passage",
            to_class_name="Document",
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        passage = client.data_object.get_by_id(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert len(passage["properties"]["ofDocument"]) == 1

    for i in range(0, len(passage_uuids)):
        client.data_object.reference.update(
            passage_uuids[i],
            "ofDocument",
            document_uuids[i],
            from_class_name="Passage",
            to_class_names="Document",
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        client.data_object.reference.delete(
            passage_uuids[i],
            "ofDocument",
            document_uuids[i],
            from_class_name="Passage",
            to_class_name="Document",
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        passage = client.data_object.get_by_id(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert len(passage["properties"]["ofDocument"]) == 0

    for i in range(0, len(passage_uuids)):
        client.data_object.delete(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )

    for i in range(0, len(passage_uuids)):
        exists = client.data_object.exists(
            class_name=class_name_passage,
            uuid=passage_uuids[i],
            tenant=tenants[i].name,
        )
        assert not exists

    for i in range(0, len(document_uuids)):
        client.data_object.delete(
            class_name=class_name_document,
            uuid=document_uuids[i],
            tenant=tenants[i].name,
        )

    for i in range(0, len(document_uuids)):
        exists = client.data_object.exists(
            class_name=class_name_document,
            uuid=document_uuids[i],
            tenant=tenants[i].name,
        )
        assert not exists


@pytest.mark.parametrize(
    "prop_defs,props",
    [
        (
            {
                "dataType": ["text"],
                "name": "name",
            },
            {
                "name": "test",
            },
        ),
        (
            {
                "dataType": ["text[]"],
                "name": "names",
            },
            {
                "names": ["test1", "test2"],
            },
        ),
        (
            {
                "dataType": ["int"],
                "name": "age",
            },
            {
                "age": 42,
            },
        ),
        (
            {
                "dataType": ["int[]"],
                "name": "ages",
            },
            {
                "ages": [42, 43],
            },
        ),
        (
            {
                "dataType": ["number"],
                "name": "height",
            },
            {
                "height": 1.80,
            },
        ),
        (
            {
                "dataType": ["number[]"],
                "name": "heights",
            },
            {
                "heights": [1.00, 1.80],
            },
        ),
        (
            {
                "dataType": ["boolean"],
                "name": "isTall",
            },
            {
                "isTall": True,
            },
        ),
        (
            {
                "dataType": ["boolean[]"],
                "name": "areTall",
            },
            {
                "areTall": [False, True],
            },
        ),
        (
            {
                "dataType": ["date"],
                "name": "birthday",
            },
            {
                "birthday": "2021-01-01T00:00:00Z",
            },
        ),
        (
            {
                "dataType": ["date[]"],
                "name": "birthdays",
            },
            {
                "birthdays": ["2021-01-01T00:00:00Z", "2021-01-02T00:00:00Z"],
            },
        ),
    ],
)
def test_nested_object_datatype(prop_defs: dict, props: dict):
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    client.schema.create_class(
        {
            "class": "A",
            "properties": [
                {"name": "nested", "dataType": ["object"], "nestedProperties": [prop_defs]},
            ],
            "vectorizer": "none",
        }
    )

    uuid_ = client.data_object.create({"nested": props}, "A")
    obj = client.data_object.get_by_id(uuid_, class_name="A")
    assert obj["properties"]["nested"] == props

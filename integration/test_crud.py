import json
import os
import time
from datetime import datetime
from datetime import timezone
from typing import List

import pytest

import weaviate


def get_query_for_group(name):
    return ("""
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
    """ % name)


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


@pytest.fixture(scope="module")
def people_schema() -> str:
    with open(os.path.join(os.path.dirname(__file__), "people_schema.json"), encoding='utf-8') as f:
        return json.load(f)


def test_load_scheme(people_schema):
    client = weaviate.Client("http://localhost:8080")
    client.schema.create(people_schema)

    assert client.schema.contains()
    assert client.schema.contains(people_schema)

    for cls in people_schema["classes"]:
        client.schema.delete_class(cls["class"])


@pytest.fixture(scope="module")
def client(people_schema):
    client = weaviate.Client("http://localhost:8080")
    client.schema.create(people_schema)

    yield client
    client.schema.delete_all()


@pytest.mark.parametrize("timeout, error", [(None, TypeError), ((5,), ValueError)])
def test_timeout_error(timeout, error):
    with pytest.raises(error):
        weaviate.Client("http://localhost:8080", timeout_config=timeout)


@pytest.mark.parametrize("timeout", [(5, 5), 5, 5., (5., 5.), (5, 5.)])
def test_timeout(people_schema, timeout):
    client = weaviate.Client("http://localhost:8080", timeout_config=timeout)
    client.schema.create(people_schema)
    expected_name = "Sophie Scholl"
    client.data_object.create({"name": expected_name}, "Person", "594b7827-f795-40d0-aabb-5e0553953dad")
    time.sleep(0.5)
    result = client.query.raw(gql_get_sophie_scholl)
    assert result["data"]["Get"]["Person"][0]["name"] == expected_name
    client.schema.delete_all()


def test_query_data(client):
    expected_name = "Sophie Scholl"
    client.data_object.create({"name": expected_name}, "Person", "594b7827-f795-40d0-aabb-5e0553953dad")
    time.sleep(2.0)
    result = client.query.raw(gql_get_sophie_scholl)
    assert result["data"]["Get"]["Person"][0]["name"] == expected_name


def test_create_schema():
    client = weaviate.Client("http://localhost:8080")
    single_class = {
        "class": "Barbecue",
        "description": "Barbecue or BBQ where meat and vegetables get grilled"
    }
    client.schema.create_class(single_class)
    prop = {
        "dataType": ["string"],
        "description": "how hot is the BBQ in C",
        "name": "heat",
    }
    client.schema.property.create("Barbecue", prop)
    classes = client.schema.get()['classes']
    found = False
    for class_ in classes:
        if class_["class"] == "Barbecue":
            found = len(class_['properties']) == 1
    assert found
    client.schema.delete_class("Barbecue")


def test_replace_and_update(client):
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


def test_crud(client):
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
    local_client.data_object.create({"name": "Andrew S. Tanenbaum"}, "Person", "28954261-0449-57a2-ade5-e9e08d11f51a")
    local_client.data_object.create({"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
    local_client.data_object.create({"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642")
    local_client.data_object.create({"name": "Tim Berners-Lee"}, "Person", "d1e90d26-d82e-5ef8-84f6-ca67119c7998")
    local_client.data_object.create({"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6")
    local_client.data_object.create({"name": "Chemists"}, "Group", "577887c1-4c6b-5594-aa62-f0c17883d9bf")

    for name in ["Marie Curie", "Fritz Haber", "Walter White"]:
        chemists.append(local_client.data_object.create({"name": name}, "Person"))

    local_time = datetime.now(timezone.utc).astimezone()
    local_client.data_object.create({"start": local_time.isoformat()}, "Call",
                                    "3ab05e06-2bb2-41d1-b5c5-e044f3aa9623")


def _create_references(local_client: weaviate.Client, chemists: List[str]):
    local_client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members",
                                           "b36268d4-a6b5-5274-985f-45f13ce0c642", from_class_name="Group",
                                           to_class_name="Person")
    local_client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members",
                                           "1c9cd584-88fe-5010-83d0-017cb3fcb446", from_class_name="Group",
                                           to_class_name="Person")

    for chemist in chemists:
        local_client.batch.add_reference("577887c1-4c6b-5594-aa62-f0c17883d9bf", "Group", "members",
                                         chemist, to_object_class_name="Person")

    local_client.batch.create_references()


def _validate_data_loading(local_client: weaviate.Client):
    legends = local_client.query.raw(get_query_for_group("Legends"))['data']['Get']
    for member in legends["Group"][0]["members"]:
        assert member["name"] in ["John von Neumann", "Alan Turing"]

    group_chemists = local_client.query.raw(get_query_for_group("Chemists"))['data']['Get']
    for member in group_chemists["Group"][0]["members"]:
        assert member["name"] in ["Marie Curie", "Fritz Haber", "Walter White"]
    assert len(group_chemists["Group"][0]["members"]) == 3


def _delete_objects(local_client: weaviate.Client, chemists: List[str]):
    local_client.data_object.delete(chemists[2],
                                    class_name="Person")  # Delete Walter White not a real chemist just a legend
    time.sleep(1.1)
    assert not local_client.data_object.exists(chemists[2], class_name="Person"), "Thing was not correctly deleted"


def _delete_references(local_client: weaviate.Client):
    # Test delete reference
    prime_ministers_group = local_client.data_object.create({"name": "Prime Ministers"}, "Group")
    prime_ministers = []
    for name in ["Wim Kok", "Dries van Agt", "Piet de Jong"]:
        prime_ministers.append(local_client.data_object.create({"name": name}, "Person"))
    for prime_minister in prime_ministers:
        local_client.data_object.reference.add(prime_ministers_group, "members", prime_minister,
                                               from_class_name="Group", to_class_name="Person")
    time.sleep(2.0)
    local_client.data_object.reference.delete(prime_ministers_group, "members", prime_ministers[0],
                                              from_class_name="Group", to_class_name="Person")
    time.sleep(2.0)
    prime_ministers_group_object = local_client.data_object.get_by_id(prime_ministers_group, class_name="Group")
    assert len(prime_ministers_group_object["properties"]["members"]) == 2, "Reference not deleted correctly"


def _get_data(local_client: weaviate.Client):
    local_client.data_object.create({"name": "George Floyd"}, "Person", "452e3031-bdaa-4468-9980-aed60d0258bf")
    time.sleep(2.0)
    person = local_client.data_object.get_by_id("452e3031-bdaa-4468-9980-aed60d0258bf", ["interpretation"],
                                                with_vector=True, class_name="Person")
    assert "vector" in person
    assert "interpretation" in person["additional"], "additional property _interpretation not in person"

    persons = local_client.data_object.get(with_vector=True)
    assert "vector" in persons["objects"][0], "additional property _vector not in persons"

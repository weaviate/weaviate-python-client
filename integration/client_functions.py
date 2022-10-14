import os
import time
import weaviate

from integration.crud import IntegrationTestCrud
from integration.graphql import TestGraphQL
from integration.misc import TestMisc
from integration.classification import contextual
from integration.integration_util import TestFailedException

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

def query_data(client):
    print("Test query")
    expected_name = "Sophie Scholl"
    client.data_object.create({"name": expected_name}, "Person", "594b7827-f795-40d0-aabb-5e0553953dad")
    time.sleep(2.0)
    result = client.query.raw(gql_get_sophie_scholl)
    if result["data"]["Get"]["Person"][0]["name"] != expected_name:
        raise TestFailedException("Query result is wrong")


def creating_schema(client):
    print("Checking if weaviate is reachable")
    if not client.is_ready():
        raise TestFailedException("Weaviate not reachable")

    if client.schema.contains():
        raise TestFailedException("No schema should be present")

    print("Load a schema")
    schema_json_file = os.path.join(os.path.dirname(__file__), "people_schema.json")
    client.schema.create(schema_json_file)

    if not client.schema.contains():
        raise TestFailedException("Weaviate does not contain loaded schema")
    
    original_schema = weaviate.util._get_dict_from_object(schema_json_file)
    if not client.schema.contains(original_schema):
        raise TestFailedException("Loaded schema does not match the one from Weaviate!")

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
    if not found:
        raise TestFailedException("Class property not added properly")


if __name__ == "__main__":
    print("Weaviate should be running at local host 8080")
    client = weaviate.Client("http://localhost:8080")
    creating_schema(client)
    integration = IntegrationTestCrud(client)
    integration.test_crud()
    query_data(client)

    gql_integration = TestGraphQL(client)
    gql_integration.get_data()
    gql_integration.aggregate_data()

    misc_integration = TestMisc(client)
    misc_integration.test()

    contextual(client)

    print("Integration test finished successfully")

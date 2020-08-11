import os
import time
import weaviate
from integration.queries import *
from integration.crud import IntegrationTestCrud


def query_data(w):
    print("Test query")
    expected_name = "Sophie Scholl"
    w.data_object.create({"name": expected_name}, "Person", "594b7827-f795-40d0-aabb-5e0553953dad")
    time.sleep(2.0)
    result = w.query.raw(gql_get_sophie_scholl)
    if result["data"]["Get"]["Things"]["Person"][0]["name"] != expected_name:
        print("Query result is wrong")
        exit(10)


def creating_schema(w):
    print("Checking if weaviate is reachable")
    if not w.is_reachable():
        print("Weaviate not reachable")
        exit(2)

    if w.schema.contains():
        print("No schema should be present")
        exit(3)

    print("Load a schema")
    schema_json_file = os.path.join(os.path.dirname(__file__), "../ci/people_schema.json")
    w.schema.create(schema_json_file)

    if not w.schema.contains():
        print("Weaviate does not contain loaded schema")
        exit(4)


if __name__ == "__main__":
    print("Weaviate should be running at local host 8080")
    w = weaviate.Client("http://localhost:8080")
    creating_schema(w)
    integration = IntegrationTestCrud(w)

    integration.test_crud()

    query_data(w)

    print("Integration test finished successfully")

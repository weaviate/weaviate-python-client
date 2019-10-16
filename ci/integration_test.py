import weaviate
import os

print("Weaviate should be running at local host 8080")
w = weaviate.Weaviate("http://localhost:8080")

print("Checking if weaviate is reachable")
if not w.is_reachable():
    exit(1)

print("Load a schema")
schema_json_file = os.path.join(os.path.dirname(__file__), "people_schema.json")
w.create_schema(schema_json_file)

print("Create a batch with data")
batch = weaviate.batch.ThingsBatchRequest()
batch.add_thing({"name": "Marie Curie"}, "Person")
batch.add_thing({"name": "John Rawls"}, "Person")

print("Load batch")
w.create_things_in_batch(batch)

print("Integration test successfully completed")
exit(0)

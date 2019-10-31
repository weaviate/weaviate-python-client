import os
from queries import *
import time

print("Weaviate should be running at local host 8080")
w = weaviate.Client("http://localhost:8080")

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

print("Load a single things")
w.create_thing({"name": "Andrew S. Tanenbaum"}, "Person", "28954261-0449-57a2-ade5-e9e08d11f51a")
w.create_thing({"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
w.create_thing({"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642")
w.create_thing({"name": "Tim Berners-Lee"}, "Person", "d1e90d26-d82e-5ef8-84f6-ca67119c7998")

w.create_thing({"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6")

time.sleep(1.1)  # Let weaviate refresh its index with the newly loaded things

print("Add reference to thing")
w.add_reference_to_thing("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "b36268d4-a6b5-5274-985f-45f13ce0c642")
w.add_reference_to_thing("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "1c9cd584-88fe-5010-83d0-017cb3fcb446")

print("SKIP Add reference to thing in batch (not supported atm.)")

time.sleep(1.1)  # Let weaviate refresh its index with the newly updated things

print("Validate if loading was successful")
legends = query_data(gql_get_group_legends)
for member in legends["Group"][0]["Members"]:
    if not member["name"] in ["John von Neumann", "Alan Turing"]:
        print("Adding references to things failed")
        exit(1)

print("Integration test successfully completed")
exit(0)

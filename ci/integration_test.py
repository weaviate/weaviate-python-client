import os
import time
#from queries import *
# TODO DELETE
import weaviate
from ci.queries import *



print("Weaviate should be running at local host 8080")
w = weaviate.Client("http://localhost:8080")

print("Checking if weaviate is reachable")
if not w.is_reachable():
    print("Weaviate not reachable")
    exit(2)

if w.contains_schema():
    print("No schema should be present")
    exit(3)

print("Load a schema")
schema_json_file = os.path.join(os.path.dirname(__file__), "people_schema.json")
w.create_schema(schema_json_file)

if not w.contains_schema():
    print("Weaviate does not contain loaded schema")
    exit(4)

print("Create a batch with data")
batch = weaviate.batch.ThingsBatchRequest()

batch.add_thing({"name": "John Rawls"}, "Person")
batch.add_thing({"name": "Emanuel Kant"}, "Person")
batch.add_thing({"name": "Plato"}, "Person")


print("Load batch")
w.create_things_in_batch(batch)

print("Load a single things")
w.create_thing({"name": "Andrew S. Tanenbaum"}, "Person", "28954261-0449-57a2-ade5-e9e08d11f51a")
w.create_thing({"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
w.create_thing({"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642")
w.create_thing({"name": "Tim Berners-Lee"}, "Person", "d1e90d26-d82e-5ef8-84f6-ca67119c7998")

w.create_thing({"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6")
w.create_thing({"name": "Chemists"}, "Group", "577887c1-4c6b-5594-aa62-f0c17883d9bf")

chemists = [None]*3
chemists[0] = w.create_thing({"name": "Marie Curie"}, "Person")
chemists[1] = w.create_thing({"name": "Fritz Haber"}, "Person")
chemists[2] = w.create_thing({"name": "Walter White"}, "Person")

time.sleep(1.1)  # Let weaviate refresh its index with the newly loaded things

print("Add reference to thing")
w.add_reference_to_thing("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "b36268d4-a6b5-5274-985f-45f13ce0c642")
w.add_reference_to_thing("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "1c9cd584-88fe-5010-83d0-017cb3fcb446")



print("Add reference to thing in batch")
reference_batch = weaviate.batch.ReferenceBatchRequest()

for chemist in chemists:
    reference_batch.add_reference("Group", "577887c1-4c6b-5594-aa62-f0c17883d9bf", "members", chemist)

w.add_references_in_batch(reference_batch)

time.sleep(1.1)  # Let weaviate refresh its index with the newly updated things

print("Validate if loading was successful")
legends = query_data(gql_get_group_legends)
for member in legends["Group"][0]["Members"]:
    if not member["name"] in ["John von Neumann", "Alan Turing"]:
        print("Adding references to things failed")
        exit(5)

group_chemists = query_data(gql_get_group_chemists)
for member in group_chemists["Group"][0]["Members"]:
    if not member["name"] in ["Marie Curie", "Fritz Haber", "Walter White"]:
        print("Adding references to things failed")
        exit(6)
if len(group_chemists["Group"][0]["Members"]) != 3:
    exit(7)

print("Test Delete")
w.delete_thing(chemists[2])  # Delete Walter White not a real chemist just a legend
time.sleep(1.1)
if w.get_thing(chemists[2]) is not None:
    print("Thing was not correctly deleted")
    exit(8)

# Test delete reference
prime_ministers_group = w.create_thing({"name": "Prime Ministers"}, "Group")
prime_ministers = []
prime_minister_names = ["Wim Kok", "Dries van Agt", "Piet de Jong"]
for name in prime_minister_names:
    prime_ministers.append(w.create_thing({"name": name}, "Person"))
time.sleep(1.2)
for prime_minister in prime_ministers:
    w.add_reference_to_thing(prime_ministers_group, "members", prime_minister)
time.sleep(1.2)
w.delete_reference_from_thing(prime_ministers_group, "members", prime_ministers[0])

# TODO test some how query seems to fail raiscondition or result set not big enough


# len(group_prime_ministers["Group"][0]["Members"][0]) != 3:
#     print("Reference not deleted correctly")
#     exit(9)


print("Test query")
expected_name = "Sophie Scholl"
w.create_thing({"name": expected_name}, "Person", "28935261-0449-56a2-ade5-e9e08d11f51a")
result = w.query(gql_get_sophie_scholl)
if result["data"]["Get"]["Things"]["Person"][0]["name"] != expected_name:
    print("Query result is wrong")
    exit(10)

print("Integration test successfully completed")
exit(0)

import weaviate
import time

client = weaviate.Client("http://localhost:8080")
client.schema.create("https://raw.githubusercontent.com/semi-technologies/weaviate-python-client/master/documentation/getting_started/people_schema.json")

client.data_object.create({"name": "John von Neumann"}, "Person", "b36268d4-a6b5-5274-985f-45f13ce0c642")
client.data_object.create({"name": "Alan Turing"}, "Person", "1c9cd584-88fe-5010-83d0-017cb3fcb446")
client.data_object.create({"name": "Legends"}, "Group", "2db436b5-0557-5016-9c5f-531412adf9c6")

time.sleep(2.0)

client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "b36268d4-a6b5-5274-985f-45f13ce0c642")
client.data_object.reference.add("2db436b5-0557-5016-9c5f-531412adf9c6", "members", "1c9cd584-88fe-5010-83d0-017cb3fcb446")




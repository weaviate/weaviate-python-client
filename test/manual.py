import weaviate
from unittest.mock import Mock

w = weaviate.Weaviate("http://localhost:8080")

batch = weaviate.batch.ThingsBatchRequest()
place1 = {
    "name": "Lebowski"
}
place2 = {
    "name": "ACU"
}

batch.add_thing(place1, "Place")
batch.add_thing(place2, "Place")

w.create_things_in_batch(batch)

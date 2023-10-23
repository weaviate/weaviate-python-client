import uuid

import weaviate

schema = {
    "classes": [
        {
            "class": "ClassA",
            "properties": [
                {"dataType": ["string"], "name": "stringProp"},
                {"dataType": ["int"], "name": "intProp"},
            ],
        }
    ]
}


def test_low_timeout():
    client = weaviate.Client("http://localhost:8080", timeout_config=(1, 1))
    client.schema.delete_all()
    client.schema.create(schema)
    client.batch.configure(dynamic=True, batch_size=10, num_workers=4)

    num_objects = (
        5000  # cannot be increased too high, because weaviate can't return that many results
    )
    uuids = []
    for i in range(num_objects):
        uuids.append(uuid.uuid4())
        client.batch.add_data_object(
            {"stringProp": f"object-{i}", "intProp": i}, "ClassA", uuid=uuids[-1]
        )
    client.batch.flush()
    result = client.query.aggregate("ClassA").with_meta_count().do()
    assert num_objects == result["data"]["Aggregate"]["ClassA"][0]["meta"]["count"]

    # update all objects to make sure that updates are processed even when timeouts occur
    for i in range(num_objects):
        client.batch.add_data_object(
            {"stringProp": f"object-{i*2}", "intProp": i * 2}, "ClassA", uuid=uuids[i]
        )
    client.batch.flush()

    result = client.query.aggregate("ClassA").with_meta_count().do()
    assert num_objects == result["data"]["Aggregate"]["ClassA"][0]["meta"]["count"]

    # check that no additional objects where created, but everything was updated
    result = (
        client.query.get("ClassA", ["intProp"])
        .with_additional("id")
        .with_limit(num_objects + 10)
        .do()
    )
    assert num_objects == len(result["data"]["Get"]["ClassA"])
    for obj in result["data"]["Get"]["ClassA"]:
        uuid_ind = uuids.index(uuid.UUID(obj["_additional"]["id"]))
        assert int(obj["intProp"]) == uuid_ind * 2

    client.schema.delete_all()

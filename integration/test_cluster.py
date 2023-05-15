import pytest

import weaviate

GIT_HASH = "c804a73"
SERVER_VERSION = "1.19.3"
NODE_NAME = "node1"
NUM_OBJECT = 10

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


@pytest.fixture(scope="module")
def client():
    client = weaviate.Client("http://localhost:8080")
    client.schema.delete_all()
    yield client
    client.schema.delete_all()


def test_get_nodes_status_without_data(client):
    """get nodes status without data"""
    resp = client.cluster.get_nodes_status()
    assert len(resp) == 1
    assert resp[0]["gitHash"] == GIT_HASH
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 0
    assert resp[0]["stats"]["objectCount"] == 0
    assert resp[0]["stats"]["shardCount"] == 0
    assert resp[0]["status"] == "HEALTHY"
    assert resp[0]["version"] == SERVER_VERSION


def test_get_nodes_status_with_data(client):
    """get nodes status with data"""
    class_name = "ClassA"
    client.schema.create(schema)
    for i in range(NUM_OBJECT):
        client.data_object.create({"stringProp": f"object-{i}", "intProp": i}, "ClassA")

    resp = client.cluster.get_nodes_status()
    assert len(resp) == 1
    assert resp[0]["gitHash"] == GIT_HASH
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 1
    assert resp[0]["shards"][0]["class"] == class_name
    assert resp[0]["shards"][0]["objectCount"] == NUM_OBJECT
    assert resp[0]["stats"]["objectCount"] == NUM_OBJECT
    assert resp[0]["stats"]["shardCount"] == 1
    assert resp[0]["status"] == "HEALTHY"
    assert resp[0]["version"] == SERVER_VERSION

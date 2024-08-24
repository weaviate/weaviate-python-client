import pytest

import weaviate
from weaviate.collections.classes.config import (
    Configure,
    DataType,
    Property,
)
from weaviate.util import parse_version_string


NODE_NAME = "node1"
NUM_OBJECT = 10


@pytest.fixture(scope="module")
def client():
    client = weaviate.connect_to_local()
    client.collections.delete_all()
    yield client
    client.collections.delete_all()


def test_rest_nodes_without_data(client: weaviate.WeaviateClient):
    """get nodes status without data"""
    resp = client.cluster.rest_nodes(output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert resp[0]["shards"] is None
    assert resp[0]["stats"]["objectCount"] == 0
    assert resp[0]["stats"]["shardCount"] == 0
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]


def test_rest_nodes_with_data(client: weaviate.WeaviateClient):
    """get nodes status with data"""
    collection_name_1 = "Collection_1"
    uncap_collection_name_1 = "collection_1"
    collection = client.collections.create(
        name=collection_name_1,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many([{"Name": f"name {i}"} for i in range(NUM_OBJECT)])

    collection_name_2 = "Collection_2"
    collection = client.collections.create(
        name=collection_name_2,
        properties=[Property(name="Name", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many([{"Name": f"name {i}"} for i in range(NUM_OBJECT * 2)])

    # server behaviour changed by https://github.com/weaviate/weaviate/pull/4203
    server_is_at_least_124 = parse_version_string(
        client.get_meta()["version"]
    ) > parse_version_string("1.24")

    resp = client.cluster.rest_nodes(output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 2
    assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT * 3
    assert resp[0]["stats"]["shardCount"] == 2
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]

    shards = sorted(resp[0]["shards"], key=lambda x: x["class"])
    assert shards[0]["class"] == collection_name_1
    assert shards[0]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT
    assert shards[1]["class"] == collection_name_2
    assert shards[1]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT * 2

    resp = client.cluster.rest_nodes(collection=collection_name_1, output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 1
    assert resp[0]["stats"]["shardCount"] == 1
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]
    assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT

    resp = client.cluster.rest_nodes(uncap_collection_name_1, output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 1
    assert resp[0]["stats"]["shardCount"] == 1
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]
    assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT

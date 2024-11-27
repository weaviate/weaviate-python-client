from typing import Dict, Any

import pytest

import weaviate
from weaviate.util import parse_version_string

NODE_NAME = "node1"
NUM_OBJECT = 10


def schema(class_name: str) -> Dict[str, Any]:
    return {
        "classes": [
            {
                "class": class_name,
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


def test_get_nodes_status_without_data(client: weaviate.Client):
    """get nodes status without data"""
    resp = client.cluster.get_nodes_status(output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert resp[0]["shards"] is None  # no class given
    assert resp[0]["stats"]["objectCount"] == 0
    assert resp[0]["stats"]["shardCount"] == 0
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]


def test_get_nodes_status_with_data(client: weaviate.Client):
    """get nodes status with data"""
    class_name1 = "ClassA"
    uncap_class_name1 = "classA"
    client.schema.create(schema(class_name1))
    for i in range(NUM_OBJECT):
        client.data_object.create({"stringProp": f"object-{i}", "intProp": i}, class_name1)

    class_name2 = "ClassB"
    client.schema.create(schema(class_name2))
    for i in range(NUM_OBJECT * 2):
        client.data_object.create({"stringProp": f"object-{i}", "intProp": i}, class_name2)

    # server behaviour of resp.stats.objectCount changed by # server behaviour changed by https://github.com/weaviate/weaviate/pull/4203

    server_is_at_least_124 = parse_version_string(
        client._connection._server_version
    ) > parse_version_string("1.24")

    resp = client.cluster.get_nodes_status(output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 2
    assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT * 3
    assert resp[0]["stats"]["shardCount"] == 2
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]

    shards = sorted(resp[0]["shards"], key=lambda x: x["class"])
    assert shards[0]["class"] == class_name1
    assert shards[0]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT
    assert shards[1]["class"] == class_name2
    assert shards[1]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT * 2

    resp = client.cluster.get_nodes_status(class_name1, output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 1
    assert resp[0]["stats"]["shardCount"] == 1
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]

    assert shards[0]["class"] == class_name1
    assert shards[0]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT
    assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT

    resp = client.cluster.get_nodes_status(uncap_class_name1, output="verbose")
    assert len(resp) == 1
    assert "gitHash" in resp[0]
    assert resp[0]["name"] == NODE_NAME
    assert len(resp[0]["shards"]) == 1
    assert resp[0]["stats"]["shardCount"] == 1
    assert resp[0]["status"] == "HEALTHY"
    assert "version" in resp[0]

    assert shards[0]["class"] == class_name1
    assert shards[0]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT
    assert resp[0]["stats"]["objectCount"] == 0 if server_is_at_least_124 else NUM_OBJECT


def test_get_cluster_statistics(client: weaviate.Client):

    if not client._connection._weaviate_version.is_lower_than(1, 25, 0):
        pytest.skip("Cluster statistics are supported in versions higher than 1.25.0")

    """Test getting cluster statistics."""
    stats = client.cluster.get_cluster_statistics()

    # Check top level structure
    assert "statistics" in stats
    assert "synchronized" in stats
    assert isinstance(stats["synchronized"], bool)

    # Check statistics array
    assert isinstance(stats["statistics"], list)
    assert len(stats["statistics"]) >= 1  # At least one node

    # Check first node's statistics
    node = stats["statistics"][0]
    # bootstrapped is optional
    if "bootstrapped" in node:
        assert isinstance(node["bootstrapped"], bool)
    assert isinstance(node["candidates"], dict)
    # Check candidates structure if not empty
    if node["candidates"]:
        for node_name, address in node["candidates"].items():
            assert isinstance(node_name, str)
            assert isinstance(address, str)
            assert ":" in address  # Address should be in format IP:PORT
    assert isinstance(node["dbLoaded"], bool)
    assert isinstance(node["isVoter"], bool)
    assert isinstance(node["leaderAddress"], str)
    assert isinstance(node["leaderId"], str)
    assert isinstance(node["name"], str)
    assert isinstance(node["open"], bool)  # API returns 'open', not 'open_'
    assert isinstance(node["ready"], bool)
    assert isinstance(node["status"], str)

    # Check Raft statistics
    raft = node["raft"]
    assert isinstance(raft["appliedIndex"], str)
    assert isinstance(raft["commitIndex"], str)
    assert isinstance(raft["fsmPending"], str)
    assert isinstance(raft["lastContact"], str)
    assert isinstance(raft["lastLogIndex"], str)
    assert isinstance(raft["lastLogTerm"], str)
    assert isinstance(raft["lastSnapshotIndex"], str)
    assert isinstance(raft["lastSnapshotTerm"], str)
    assert isinstance(raft["latestConfiguration"], list)
    assert isinstance(raft["latestConfigurationIndex"], str)
    assert isinstance(raft["numPeers"], str)
    assert isinstance(raft["protocolVersion"], str)
    assert isinstance(raft["protocolVersionMax"], str)
    assert isinstance(raft["protocolVersionMin"], str)
    assert isinstance(raft["snapshotVersionMax"], str)
    assert isinstance(raft["snapshotVersionMin"], str)
    assert isinstance(raft["state"], str)
    assert isinstance(raft["term"], str)

    # Check at least one peer in the configuration
    assert len(raft["latestConfiguration"]) >= 1
    peer = raft["latestConfiguration"][0]
    assert isinstance(peer["address"], str)
    assert isinstance(peer["id"], str)  # API returns 'id', not 'id_'
    assert isinstance(peer["suffrage"], int)

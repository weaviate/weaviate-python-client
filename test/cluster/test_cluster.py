import unittest

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.cluster.cluster import Cluster
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    EmptyResponseException,
)


class TestCluster(unittest.TestCase):
    def test_get_nodes_status(self):
        # error messages

        unexpected_err_msg = "Nodes status"
        empty_response_err_msg = "Nodes status response returned empty"
        connection_err_msg = "Get nodes status failed due to connection error"

        # expected failure
        mock_conn = mock_connection_func("get", status_code=500)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Cluster(mock_conn).get_nodes_status()
        check_startswith_error_message(self, error, unexpected_err_msg)

        mock_conn = mock_connection_func("get", status_code=200, return_json={"nodes": []})
        with self.assertRaises(EmptyResponseException) as error:
            Cluster(mock_conn).get_nodes_status()
        check_error_message(self, error, empty_response_err_msg)

        mock_conn = mock_connection_func("get", side_effect=RequestsConnectionError)
        with self.assertRaises(RequestsConnectionError) as error:
            Cluster(mock_conn).get_nodes_status()
        check_error_message(self, error, connection_err_msg)

        # expected success
        expected_resp = {
            "nodes": [
                {
                    "gitHash": "abcd123",
                    "name": "node1",
                    "shards": [{"class": "SomeClass", "name": "1qa2ws3ed", "objectCount": 100}],
                    "stats": {"objectCount": 100, "shardCount": 1},
                    "status": "",
                    "version": "x.x.x",
                }
            ]
        }
        mock_conn = mock_connection_func("get", status_code=200, return_json=expected_resp)
        result = Cluster(mock_conn).get_nodes_status()
        self.assertListEqual(result, expected_resp.get("nodes"))
        mock_conn.get.assert_called_with(path="/nodes")

    def test_get_cluster_statistics(self):
        # error messages
        unexpected_err_msg = "Cluster statistics"
        empty_response_err_msg = "Cluster statistics response returned empty"
        connection_err_msg = "Get cluster statistics failed due to connection error"

        # expected failure
        mock_conn = mock_connection_func("get", status_code=500)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Cluster(mock_conn).get_cluster_statistics()
        check_startswith_error_message(self, error, unexpected_err_msg)

        mock_conn = mock_connection_func("get", status_code=200, return_json=None)
        with self.assertRaises(EmptyResponseException) as error:
            Cluster(mock_conn).get_cluster_statistics()
        check_error_message(self, error, empty_response_err_msg)

        mock_conn = mock_connection_func("get", side_effect=RequestsConnectionError)
        with self.assertRaises(RequestsConnectionError) as error:
            Cluster(mock_conn).get_cluster_statistics()
        check_error_message(self, error, connection_err_msg)

        # expected success
        expected_resp = {
            "statistics": [
                {
                    "candidates": {
                        "weaviate-0": "10.244.2.3:8300",
                        "weaviate-1": "10.244.1.3:8300",
                    },
                    "dbLoaded": True,
                    "isVoter": True,
                    "leaderAddress": "10.244.3.3:8300",
                    "leaderId": "weaviate-2",
                    "name": "weaviate-0",
                    "open_": True,
                    "raft": {
                        "appliedIndex": "3",
                        "commitIndex": "3",
                        "fsmPending": "0",
                        "lastContact": "29.130625ms",
                        "lastLogIndex": "3",
                        "lastLogTerm": "2",
                        "lastSnapshotIndex": "0",
                        "lastSnapshotTerm": "0",
                        "latestConfiguration": [
                            {"address": "10.244.1.3:8300", "id_": "weaviate-1", "suffrage": 0},
                            {"address": "10.244.3.3:8300", "id_": "weaviate-2", "suffrage": 0},
                            {"address": "10.244.2.3:8300", "id_": "weaviate-0", "suffrage": 0},
                        ],
                        "latestConfigurationIndex": "0",
                        "numPeers": "2",
                        "protocolVersion": "3",
                        "protocolVersionMax": "3",
                        "protocolVersionMin": "0",
                        "snapshotVersionMax": "1",
                        "snapshotVersionMin": "0",
                        "state": "Follower",
                        "term": "2",
                    },
                    "ready": True,
                    "status": "HEALTHY",
                },
                {
                    "bootstrapped": True,
                    "candidates": {},
                    "dbLoaded": True,
                    "isVoter": True,
                    "leaderAddress": "10.244.3.3:8300",
                    "leaderId": "weaviate-2",
                    "name": "weaviate-1",
                    "open_": True,
                    "raft": {
                        "appliedIndex": "3",
                        "commitIndex": "3",
                        "fsmPending": "0",
                        "lastContact": "41.289833ms",
                        "lastLogIndex": "3",
                        "lastLogTerm": "2",
                        "lastSnapshotIndex": "0",
                        "lastSnapshotTerm": "0",
                        "latestConfiguration": [
                            {"address": "10.244.1.3:8300", "id_": "weaviate-1", "suffrage": 0},
                            {"address": "10.244.3.3:8300", "id_": "weaviate-2", "suffrage": 0},
                            {"address": "10.244.2.3:8300", "id_": "weaviate-0", "suffrage": 0},
                        ],
                        "latestConfigurationIndex": "0",
                        "numPeers": "2",
                        "protocolVersion": "3",
                        "protocolVersionMax": "3",
                        "protocolVersionMin": "0",
                        "snapshotVersionMax": "1",
                        "snapshotVersionMin": "0",
                        "state": "Follower",
                        "term": "2",
                    },
                    "ready": True,
                    "status": "HEALTHY",
                },
            ],
            "synchronized": True,
        }
        mock_conn = mock_connection_func("get", status_code=200, return_json=expected_resp)
        result = Cluster(mock_conn).get_cluster_statistics()

        # Convert the response to match our type definitions with renamed fields
        for node in result["statistics"]:
            node["open_"] = node.pop("open_")
            for peer in node["raft"]["latestConfiguration"]:
                peer["id_"] = peer.pop("id_")

        self.assertEqual(result, expected_resp)
        mock_conn.get.assert_called_with(path="/cluster/statistics")

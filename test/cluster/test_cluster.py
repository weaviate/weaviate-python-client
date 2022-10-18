import unittest

from test.util import mock_connection_method, check_error_message
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    RequestsConnectionError,
    EmptyResponseException
)
from weaviate.cluster.cluster import Cluster


class TestCluster(unittest.TestCase):
    def test_get_nodes_status(self):
        # expected success
        expected_resp = {"nodes": [{
            "gitHash": "abcd123",
            "name": "node1",
            "shards": [{"class": "SomeClass", "name": "1qa2ws3ed", "objectCount": 100}],
            "stats": {"objectCount": 100, "shardCount": 1},
            "status": "",
            "version": "x.x.x"
        }]}
        mock_conn = mock_connection_method("get", status_code=200, return_json=expected_resp)
        result = Cluster(mock_conn).get_nodes_status()
        self.assertListEqual(result, expected_resp.get("nodes"))
        mock_conn.get.assert_called_with(path="/nodes")

        # expected failure
        mock_conn = mock_connection_method("get", status_code=500)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Cluster(mock_conn).get_nodes_status()
            check_error_message(self, error, "Nodes status! Unexpected status code: 500, with response body: None")
        
        mock_conn = mock_connection_method("get", status_code=200, return_json={"nodes": []})
        with self.assertRaises(EmptyResponseException) as error:
            Cluster(mock_conn).get_nodes_status()
            check_error_message(self, error, "Nodes status response returned empty")

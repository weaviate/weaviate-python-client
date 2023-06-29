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

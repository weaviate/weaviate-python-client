import unittest
import weaviate
from unittest.mock import Mock
from test.testing_util import add_run_rest_to_mock

class TestIsReachable(unittest.TestCase):
    def test_no_weaviate_rachable(self):
        w = weaviate.Client("http://localhost:8080")

        # 1. No weaviate
        try:
            self.assertFalse(w.is_reachable())
        except Exception as e:
            self.fail("Should not end up in any exception: " +str(e))


        # 2. Mock weaviate answering with status 200
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)  # return 200 for everything
        w.connection = connection_mock
        self.assertTrue(w.is_reachable())
        self.assertEqual(connection_mock.run_rest.call_count, 2,
                         "Call twice once for the meta endpoint (c11y) and once for the things for ES and etcd")

        # 3. Mock weaviate answering with status 401 (unauthorized)
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=401)  # return 200 for everything
        w.connection = connection_mock
        self.assertTrue(w.is_reachable())
        self.assertEqual(connection_mock.run_rest.call_count, 2,
                         "Call twice once for the meta endpoint (c11y) and once for the things for ES and etcd")


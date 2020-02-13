import unittest
import weaviate
from test.testing_util import add_run_rest_to_mock
from weaviate.connect import REST_METHOD_POST
import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
else:
    from unittest.mock import Mock

class TestQueryThings(unittest.TestCase):
    def test_query_gql(self):
        w = weaviate.Client("http://localhost:8081")
        try:
            w.query(12)
            self.fail("Query type error expected")
        except TypeError:
            pass

        connection_mock = Mock()  # Mock calling weaviate
        w._connection = add_run_rest_to_mock(connection_mock, status_code=200)
        gql = """
        {
          Get {
            Things {
              Person {
                name
                uuid
              }
            }
          }
        }
        """
        w.query(gql)
        connection_mock.run_rest.assert_called_with("/graphql", REST_METHOD_POST, {"query": gql})

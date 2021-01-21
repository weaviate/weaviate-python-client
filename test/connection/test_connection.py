import unittest
from unittest.mock import patch
import weaviate


class TestConnection(unittest.TestCase):

    def test_run_rest(self):
        """
        Test run rest casses.
        """

        connection = weaviate.connect.Connection("http://weaviate:1234")

        with patch("weaviate.connect.connection.requests") as mock_run_rest:
            mock_run_rest.get.return_value = "GET"
            mock_run_rest.put.return_value = "PUT"
            mock_run_rest.post.return_value = "POST"
            mock_run_rest.patch.return_value = "PATCH"
            mock_run_rest.delete.return_value = "DELETE"

            # GET method
            self.assertEqual(
                connection.run_rest("path", weaviate.connect.REST_METHOD_GET, {}, {}),
                "GET"
            )
            # PUT method
            self.assertEqual(
                connection.run_rest("path", weaviate.connect.REST_METHOD_PUT, {}, {}),
                "PUT"
            )
            # POST method
            self.assertEqual(
                connection.run_rest("path", weaviate.connect.REST_METHOD_POST, {}, {}),
                "POST"
            )
            # PATCH method
            self.assertEqual(
                connection.run_rest("path", weaviate.connect.REST_METHOD_PATCH, {}, {}),
                "PATCH"
            )
            # DELETE method
            self.assertEqual(
                connection.run_rest("path", weaviate.connect.REST_METHOD_DELETE, {}, {}),
                "DELETE"
            )
        


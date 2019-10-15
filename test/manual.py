import weaviate
from unittest.mock import Mock

def run_rest_raise_connection_error(x, y, z):
    raise ConnectionError


w = weaviate.Weaviate("http://semi.testing.eu:8080")
connection_mock = Mock()  # Mock calling weaviate
connection_mock.run_rest.side_effect = run_rest_raise_connection_error
w.connection = connection_mock

w.create_thing({"name": "Alan Greenspan"}, "CoolestPersonEver")

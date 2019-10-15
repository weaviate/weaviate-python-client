import unittest
import weaviate
from unittest.mock import Mock

class TestAddThings(unittest.TestCase):
    def test_create_thing_flawed_input(self):
        w = weaviate.Weaviate("http://localhost:8080")
        try:
            w.create_thing(None, "Class")
            self.fail("Thing was not given but accepted anyways")
        except TypeError:
            pass
        try:
            w.create_thing(224345, "Class")
            self.fail("Thing is of wrong type but no error")
        except TypeError:
            pass
        try:
            w.create_thing({'name': 'Optimus Prime'}, None)
            self.fail("Class name has wrong type")
        except TypeError:
            pass
        try:
            w.create_thing({'name': 'Optimus Prime'}, "Transformer", 19210)
            self.fail("Uuid wrong type")
        except TypeError:
            pass
        try:
            w.create_thing({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")
            self.fail("Uuid wrong form")
        except ValueError:
            pass

    def test_create_thing_connection_error(self):
        w = weaviate.Weaviate("http://semi.testing.eu:8080")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w.connection = connection_mock
        try:
            w.create_thing({"name": "Alan Greenspan"}, "CoolestPersonEver")
        except ConnectionError as e:
            pass


def run_rest_raise_connection_error(x, y, z):
    raise ConnectionError
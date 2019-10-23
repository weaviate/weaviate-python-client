import unittest
import weaviate
from unittest.mock import Mock
from test.testing_util import run_rest_raise_connection_error


class TestAddThings(unittest.TestCase):
    def test_create_thing_flawed_input(self):
        w = weaviate.Client("http://localhost:8080")
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
        w = weaviate.Client("http://semi.testing.eu:8080")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w.connection = connection_mock
        try:
            w.create_thing({"name": "Alan Greenspan"}, "CoolestPersonEver")
        except ConnectionError as e:
            pass

    def test_generate_local_things_beacon(self):
        try:
            weaviate.generate_local_things_beacon(None)
            self.fail("TypeError expected should be str")
        except TypeError:
            pass
        try:
            weaviate.generate_local_things_beacon("Leeroy Jenkins")
            self.fail("Value error expected should be uuid")
        except ValueError:
            pass

        beacon = weaviate.generate_local_things_beacon("fcf33178-1b5d-5174-b2e7-04a2129dd35a")
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/things/fcf33178-1b5d-5174-b2e7-04a2129dd35a")


import unittest
import weaviate
from test.testing_util import run_rest_raise_connection_error
from requests.exceptions import ConnectionError
from test.testing_util import add_run_rest_to_mock
from weaviate.connect import REST_METHOD_POST
import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
else:
    from unittest.mock import Mock


class TestAddAction(unittest.TestCase):
    def test_create_action_flawed_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.create_action(None, "Class")
            self.fail("action was not given but accepted anyways")
        except TypeError:
            pass
        try:
            w.create_action(224345, "Class")
            self.fail("action is of wrong type but no error")
        except TypeError:
            pass
        try:
            w.create_action({'name': 'Optimus Prime'}, None)
            self.fail("Class name has wrong type")
        except TypeError:
            pass
        try:
            w.create_action({'name': 'Optimus Prime'}, "Transformer", 19210)
            self.fail("Uuid wrong type")
        except TypeError:
            pass
        try:
            w.create_action({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")
            self.fail("Uuid wrong form")
        except ValueError:
            pass
        try:
            w.create_action({'name': 'Optimus Prime'}, "Transformer", None, 1234)
            self.fail("weight vectors wrong type")
        except TypeError:
            pass

    def test_create_action_connection_error(self):
        if sys.version_info[0] == 2:
            # Test is not working on version 2 because of old mock object
            return
        w = weaviate.Client("http://semi.testing.eu:8080")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w._connection = connection_mock
        try:
            w.create_action({"name": "Alan Greenspan"}, "CoolestPersonEver")
        except ConnectionError as e:
            pass

    def test_generate_local_actions_beacon(self):
        try:
            weaviate.generate_local_actions_beacon(None)
            self.fail("TypeError expected should be str")
        except TypeError:
            pass
        try:
            weaviate.generate_local_actions_beacon("Leeroy Jenkins")
            self.fail("Value error expected should be uuid")
        except ValueError:
            pass

        beacon = weaviate.generate_local_actions_beacon("fcf33178-1b5d-5174-b2e7-04a2129dd35a")
        self.assertTrue("beacon" in beacon)
        self.assertEqual(beacon["beacon"], "weaviate://localhost/actions/fcf33178-1b5d-5174-b2e7-04a2129dd35a")

    def test_set_vector_weigths(self):
        w = weaviate.Client("http://localhost:8081")

        # 1. Succesfully delete someaction
        connection_mock = Mock()
        w._connection = add_run_rest_to_mock(connection_mock, {"id": 0}, status_code=200)

        # action = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        # to_action = "a36268d4-a6b5-5274-985f-45f13ce0c642"

        action = {"lyrics": "da da dadadada dada, da da dadadada da, da da dadadada da, da da dadadada da Tequila"}
        class_name = "KaraokeSongs"
        vector_weights = {
            "da": "1",
            "dadadada": "w + 0.5",
            "tequila": "w*15"
        }

        rest_object = {
            "class": "KaraokeSongs",
            "schema": action,
            "vectorWeights": vector_weights
        }

        uuid = w.create_action(action, class_name, None, vector_weights)
        self.assertEqual(uuid, str(0))
        connection_mock.run_rest.assert_called_with("/actions", REST_METHOD_POST, rest_object)


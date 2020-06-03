import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *
import sys

class TestAddactions(unittest.TestCase):

    def test_create_batch_request(self):
        # Create a batch and fill it with some data
        batch = weaviate.ActionsBatchRequest()
        batch.add_action({"name": "Socrates"}, "Philosopher")
        batch.add_action({"name": "Platon"}, "Philosopher", "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        batch.add_action({"name": "Marie Curie"}, "Chemist")
        request_body = batch.get_request_body()

        # Check if the request body is right
        self.assertEqual(len(request_body["actions"]), 3, "Not all actions are in request body")
        # Are all classes present
        request_body_classes = [request_body["actions"][0]["class"], request_body["actions"][1]["class"], request_body["actions"][2]["class"]]
        self.assertTrue("Philosopher" in request_body_classes)
        self.assertTrue("Chemist" in request_body_classes)
        # Are all names present
        request_body_schema_names = [request_body["actions"][0]["schema"]["name"], request_body["actions"][1]["schema"]["name"], request_body["actions"][2]["schema"]["name"]]
        self.assertTrue("Socrates" in request_body_schema_names)
        self.assertTrue("Platon" in request_body_schema_names)
        self.assertTrue("Marie Curie" in request_body_schema_names)
        # Did the id get added properly?
        id_found = False
        for action in request_body["actions"]:
            if "id" in action:
                self.assertEqual(action["id"], "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")  # Check if id is correct
                id_found = True
        self.assertTrue(id_found)  # Check if id was in action

    def test_create_batch_request_with_changing_object(self):
        # Create a batch and fill it with some data
        batch = weaviate.ActionsBatchRequest()

        # Change the action to ensure call by reference does
        # not add the same action over and over again
        class_name = "Philosopher"
        action = {"name": "Socrates"}
        batch.add_action(action, class_name)
        action["name"] = "Platon"
        batch.add_action(action, class_name, "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        action["name"] = "Marie Curie"
        class_name = "Chemist"
        batch.add_action(action, class_name)
        request_body = batch.get_request_body()

        # Check if the request body is right
        self.assertEqual(len(request_body["actions"]), 3, "Not all actions are in request body")
        # Are all classes present
        request_body_classes = [request_body["actions"][0]["class"], request_body["actions"][1]["class"], request_body["actions"][2]["class"]]
        self.assertTrue("Philosopher" in request_body_classes)
        self.assertTrue("Chemist" in request_body_classes)
        # Are all names present
        request_body_schema_names = [request_body["actions"][0]["schema"]["name"], request_body["actions"][1]["schema"]["name"], request_body["actions"][2]["schema"]["name"]]
        self.assertTrue("Socrates" in request_body_schema_names)
        self.assertTrue("Platon" in request_body_schema_names)
        self.assertTrue("Marie Curie" in request_body_schema_names)
        # Did the id get added properly?
        id_found = False
        for action in request_body["actions"]:
            if "id" in action:
                self.assertEqual(action["id"], "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")  # Check if id is correct
                id_found = True
        self.assertTrue(id_found)  # Check if id was in action

    def test_create_batch_flawed_input(self):
        batch = weaviate.ActionsBatchRequest()
        try:
            batch.add_action(None, "Class")
            self.fail("action was not given but accepted anyways")
        except TypeError:
            pass
        try:
            batch.add_action(224345, "Class")
            self.fail("action is of wrong type but no error")
        except TypeError:
            pass
        try:
            batch.add_action({'name': 'Optimus Prime'}, None)
            self.fail("Class name has wrong type")
        except TypeError:
            pass
        try:
            batch.add_action({'name': 'Optimus Prime'}, "Transformer", 19210)
            self.fail("Uuid wrong type")
        except TypeError:
            pass
        try:
            batch.add_action({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")
            self.fail("Uuid wrong form")
        except ValueError:
            pass

    def test_add_action_batch(self):
        # test adding a normal batch
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock)
        w._connection = connection_mock

        batch = weaviate.ActionsBatchRequest()
        batch.add_action({"name": "John Rawls"}, "Philosopher", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        batch_request = {
          "fields": [
            "ALL"
          ],
          "actions": [
            {
              "class": "Philosopher",
              "schema": {
                  "name": "John Rawls"
              },
              "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
          ]
        }

        w.create_actions_in_batch(batch)

        connection_mock.run_rest.assert_called_with("/batching/actions", REST_METHOD_POST, batch_request)

    def test_add_actions_batch(self):
        # test adding a normal batch
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock)
        w._connection = connection_mock

        # Add some data to the batch
        batch = weaviate.ActionsBatchRequest()
        schemas = [{"name": "John Rawls"}, {"name": "Immanuel Kant"}, {"name": "Abraham Lincoln"}]
        classes = ["Philosopher", "Philosopher", "Politician"]
        ids = ["3fa85f64-5717-4562-b3fc-2c963f66afa6", "f2159669-6175-518b-86f8-e1ef68bd8d62"]
        batch.add_action(schemas[0], classes[0], ids[0])
        batch.add_action(schemas[1], classes[1], ids[1])
        batch.add_action(schemas[2], classes[2])

        # Create the actions from the batch
        w.create_actions_in_batch(batch)

        connection_mock.run_rest.assert_called()
        call_args = connection_mock.run_rest.call_args_list[0][0]
        self.assertEqual(call_args[0], "/batching/actions", "Path is wrong")
        self.assertEqual(call_args[1], weaviate.connect.REST_METHOD_POST)

        # Check if actions got added correctly
        actions_of_batch = call_args[2]["actions"]
        self.assertEqual(len(actions_of_batch), 3, "There where 3 actions added to the batch")

        for t in actions_of_batch:
            self.assertTrue(t["class"] in classes)
            self.assertTrue(t["schema"] in schemas)

    def test_add_actions_connection_error(self):
        if sys.version_info[0] == 2:
            # Test is not working on python 2 because of old mock
            return
        w = weaviate.Client("http://semi.testing.eu:8080")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w._connection = connection_mock

        batch = weaviate.ActionsBatchRequest()
        try:
            w.create_actions_in_batch(batch)
        except ConnectionError as e:
            pass

    def test_batch_length(self):
        batch = weaviate.ActionsBatchRequest()
        batch.add_action({"A": "B"}, "action")
        self.assertEqual(1, len(batch))
        batch.add_action({"A": "B"}, "action")
        self.assertEqual(2, len(batch))
        batch.add_action({"A": "B"}, "action")
        self.assertEqual(3, len(batch))

import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *

class TestAddThings(unittest.TestCase):

    def test_create_batch_request(self):
        # Create a batch and fill it with some data
        batch = weaviate.ThingsBatchRequest()
        batch.add_thing({"name": "Socrates"}, "Philosopher")
        batch.add_thing({"name": "Platon"}, "Philosopher", "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        batch.add_thing({"name": "Marie Curie"}, "Chemist")
        request_body = batch.get_request_body()

        # Check if the request body is right
        self.assertEqual(len(request_body["things"]), 3, "Not all things are in request body")
        # Are all classes present
        request_body_classes = [request_body["things"][0]["class"], request_body["things"][1]["class"], request_body["things"][2]["class"]]
        self.assertTrue("Philosopher" in request_body_classes)
        self.assertTrue("Chemist" in request_body_classes)
        # Are all names present
        request_body_schema_names = [request_body["things"][0]["schema"]["name"], request_body["things"][1]["schema"]["name"], request_body["things"][2]["schema"]["name"]]
        self.assertTrue("Socrates" in request_body_schema_names)
        self.assertTrue("Platon" in request_body_schema_names)
        self.assertTrue("Marie Curie" in request_body_schema_names)
        # Did the id get added properly?
        id_found = False
        for thing in request_body["things"]:
            if "id" in thing:
                self.assertEqual(thing["id"], "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")  # Check if id is correct
                id_found = True
        self.assertTrue(id_found)  # Check if id was in thing


    def test_create_batch_flawed_input(self):
        batch = weaviate.ThingsBatchRequest()
        try:
            batch.add_thing(None, "Class")
            self.fail("Thing was not given but accepted anyways")
        except TypeError:
            pass
        try:
            batch.add_thing(224345, "Class")
            self.fail("Thing is of wrong type but no error")
        except TypeError:
            pass
        try:
            batch.add_thing({'name': 'Optimus Prime'}, None)
            self.fail("Class name has wrong type")
        except TypeError:
            pass
        try:
            batch.add_thing({'name': 'Optimus Prime'}, "Transformer", 19210)
            self.fail("Uuid wrong type")
        except TypeError:
            pass
        try:
            batch.add_thing({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")
            self.fail("Uuid wrong form")
        except ValueError:
            pass

    def test_add_thing_batch(self):
        # test adding a normal batch
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock)
        w.connection = connection_mock

        batch = weaviate.ThingsBatchRequest()
        batch.add_thing({"name": "John Rawls"}, "Philosopher", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        batch_request = {
          "fields": [
            "ALL"
          ],
          "things": [
            {
              "class": "Philosopher",
              "schema": {
                  "name": "John Rawls"
              },
              "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
          ]
        }

        w.create_things_in_batch(batch)

        connection_mock.run_rest.assert_called_with("/batching/things", REST_METHOD_POST, batch_request)

    def test_add_things_batch(self):
        # test adding a normal batch
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock)
        w.connection = connection_mock

        # Add some data to the batch
        batch = weaviate.ThingsBatchRequest()
        schemas = [{"name": "John Rawls"}, {"name": "Immanuel Kant"}, {"name": "Abraham Lincoln"}]
        classes = ["Philosopher", "Philosopher", "Politician"]
        ids = ["3fa85f64-5717-4562-b3fc-2c963f66afa6", "f2159669-6175-518b-86f8-e1ef68bd8d62"]
        batch.add_thing(schemas[0], classes[0], ids[0])
        batch.add_thing(schemas[1], classes[1], ids[1])
        batch.add_thing(schemas[2], classes[2])

        # Create the things from the batch
        w.create_things_in_batch(batch)

        connection_mock.run_rest.assert_called()
        call_args = connection_mock.run_rest.call_args_list[0][0]
        self.assertEqual(call_args[0], "/batching/things", "Path is wrong")
        self.assertEqual(call_args[1], weaviate.connect.REST_METHOD_POST)

        # Check if things got added correctly
        things_of_batch = call_args[2]["things"]
        self.assertEqual(len(things_of_batch), 3, "There where 3 things added to the batch")

        for t in things_of_batch:
            self.assertTrue(t["class"] in classes)
            self.assertTrue(t["schema"] in schemas)

    def test_add_things_connection_error(self):
        w = weaviate.Client("http://semi.testing.eu:8080")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w.connection = connection_mock

        batch = weaviate.ThingsBatchRequest()
        try:
            w.create_things_in_batch(batch)
        except ConnectionError as e:
            pass
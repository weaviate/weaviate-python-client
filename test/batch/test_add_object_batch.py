import unittest
from unittest.mock import Mock
import requests
from weaviate import ObjectsBatchRequest, ReferenceBatchRequest, Client
from weaviate.connect import REST_METHOD_POST
from test.util import replace_connection, run_rest_raise_connection_error, add_run_rest_to_mock



class TestAddObjects(unittest.TestCase):

    def test_add_batch_request(self):

        # Create a batch and fill it with some data
        batch = ObjectsBatchRequest()

        request_body = batch.get_request_body()
        self.assertEqual(0, len(request_body["objects"]), "request body should be empty")

        # add an object
        batch.add({"name": "Socrates"}, "Philosopher")
        request_body = batch.get_request_body()
        self.assertEqual(1, len(request_body["objects"]), "The object is not in request body")

        # add another object
        batch.add({"name": "Platon"}, "Philosopher", "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        request_body = batch.get_request_body()
        self.assertEqual(2, len(request_body["objects"]), "Not all objects are in request body")

        # add another object
        batch.add({"name": "Marie Curie"}, "Chemist")
        request_body = batch.get_request_body()
        self.assertEqual(3, len(request_body["objects"]), "Not all objects are in request body")

        # Are all classes present
        request_body_classes = [obj["class"] for obj in request_body["objects"]]
        self.assertTrue("Philosopher" in request_body_classes)
        self.assertTrue("Chemist" in request_body_classes)

        # Are all names present
        request_body_schema_names = [obj["properties"]["name"] for obj in request_body["objects"]]
        self.assertTrue("Socrates" in request_body_schema_names)
        self.assertTrue("Platon" in request_body_schema_names)
        self.assertTrue("Marie Curie" in request_body_schema_names)

        # Did the id get added properly?
        id_found = False
        for obj in request_body["objects"]:
            if "id" in obj:
                self.assertEqual(obj["id"], "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
                id_found = True
        self.assertTrue(id_found)  # Check if id was in object

    def test_add_batch_request_with_same_variable(self):
        """
        Test add object to batch using the same variable.
        """
        # Create a batch and fill it with some data
        batch = ObjectsBatchRequest()

        # Change the object to ensure call by reference does
        # not add the same object over and over again
        class_name = "Philosopher"
        obj = {"name": "Socrates"}
        batch.add(obj, class_name)
        request_body = batch.get_request_body()
        self.assertEqual(1, len(request_body["objects"]), "The object is not in request body")

        # add another object using the same `obj` variable.
        obj["name"] = "Platon"
        batch.add(obj, class_name, "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        request_body = batch.get_request_body()
        self.assertEqual(2, len(request_body["objects"]), "Not all objects are in request body")

        # add another object using the same `obj` variable.
        obj["name"] = "Marie Curie"
        class_name = "Chemist"
        batch.add(obj, class_name)
        request_body = batch.get_request_body()
        self.assertEqual(3, len(request_body["objects"]), "Not all objects are in request body")

        # Are all classes present
        request_body_classes = [obj["class"] for obj in request_body["objects"]]
        self.assertTrue("Philosopher" in request_body_classes)
        self.assertTrue("Chemist" in request_body_classes)

        # Are all names present
        request_body_schema_names = [obj["properties"]["name"] for obj in request_body["objects"]]
        self.assertTrue("Socrates" in request_body_schema_names)
        self.assertTrue("Platon" in request_body_schema_names)
        self.assertTrue("Marie Curie" in request_body_schema_names)

        # Did the id get added properly?
        id_found = False
        for obj in request_body["objects"]:
            if "id" in obj:
                self.assertEqual(obj["id"], "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
                id_found = True
        self.assertTrue(id_found)  # Check if id was in object

    def test_add_batch_exceptions(self):
        """
        Test add batch exceptions.
        """

        batch = ObjectsBatchRequest()

        # wrong data_object
        with self.assertRaises(TypeError):
            batch.add(None, "Class")
        with self.assertRaises(TypeError):
            batch.add(224345, "Class")
        # wrong class_name
        with self.assertRaises(TypeError):
            batch.add({'name': 'Optimus Prime'}, None)
        with self.assertRaises(TypeError):
            batch.add({'name': 'Optimus Prime'}, ["Transformer"])
        # wrong uuid
        with self.assertRaises(TypeError):
            batch.add({'name': 'Optimus Prime'}, "Transformer", 19210)
        with self.assertRaises(ValueError):
            batch.add({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")

    def test_create_batch(self):
        """
        Test create batch objects.
        """
        # test adding a normal batch
        w = Client("http://localhorst:8080")

        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        batch = ObjectsBatchRequest()
        batch.add({"name": "John Rawls"}, "Philosopher", "3fa85f64-5717-4562-b3fc-2c963f66afa6")

        batch_request = {
          "fields": [
            "ALL"
          ],
          "objects": [
            {
              "class": "Philosopher",
              "properties": {
                  "name": "John Rawls"
              },
              "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
            }
          ]
        }

        # with create_objects
        w.batch.create_objects(batch)
        connection_mock.run_rest.assert_called_with(
            path="/batch/objects",
            rest_method=REST_METHOD_POST,
            weaviate_object=batch_request)

        # with create
        w.batch.create(batch)
        connection_mock.run_rest.assert_called_with(
            path="/batch/objects",
            rest_method=REST_METHOD_POST,
            weaviate_object=batch_request)

    def test_create_batch_multiple(self):
        """
        Test create batch objects.
        """
        # test adding a normal batch
        w = Client("http://localhorst:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        # Add some data to the batch
        batch = ObjectsBatchRequest()
        properties = [{"name": "John Rawls"}, {"name": "Immanuel Kant"}, \
            {"name": "Abraham Lincoln"}]
        classes = ["Philosopher", "Philosopher", "Politician"]
        ids = ["3fa85f64-5717-4562-b3fc-2c963f66afa6", "f2159669-6175-518b-86f8-e1ef68bd8d62"]
        batch.add(properties[0], classes[0], ids[0])
        batch.add(properties[1], classes[1], ids[1])
        batch.add(properties[2], classes[2])

        # Create the objects from the batch
        w.batch.create(batch)

        connection_mock.run_rest.assert_called()
        call_kwargs = connection_mock.run_rest.call_args_list[0][1]
        self.assertEqual(call_kwargs['path'], "/batch/objects", "Path is wrong")
        self.assertEqual(call_kwargs['rest_method'], REST_METHOD_POST)

        # Check if objects got added correctly
        objects_of_batch = call_kwargs['weaviate_object']["objects"]
        self.assertEqual(len(objects_of_batch), 3, "There where 3 objects added to the batch")

        for obj in objects_of_batch:
            self.assertTrue(obj["class"] in classes)
            self.assertTrue(obj["properties"] in properties)

    def test_create_objects_batch_exceptions(self):
        """
        Test batch creat objects exceptions.
        """

        client = Client("http://semi.testing.eu:8080")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        client._connection = connection_mock

        batch = ObjectsBatchRequest()
        with self.assertRaises(requests.exceptions.ConnectionError):
            client.batch.create(batch)

        ## test create for non batch object
        # with create_references
        with self.assertRaises(TypeError):
            client.batch.create_objects([10., 20.])
        with self.assertRaises(TypeError):
            client.batch.create_objects(ReferenceBatchRequest())
        # with create
        with self.assertRaises(TypeError):
            client.batch.create([10., 20.])

    def test_batch_size(self):
        """
        Test batch size.
        """

        batch = ObjectsBatchRequest()

        # empty batch
        self.assertEqual(0, len(batch))
        # add an object
        batch.add({"A": "B"}, "Object")
        self.assertEqual(1, len(batch))
        # add another object
        batch.add({"A": "B"}, "Thing")
        self.assertEqual(2, len(batch))
        # add another object
        batch.add({"A": "B"}, "Thing")
        self.assertEqual(3, len(batch))

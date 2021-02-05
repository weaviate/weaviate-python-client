import unittest
from copy import deepcopy
from unittest.mock import patch
from weaviate import ReferenceBatchRequest, ObjectsBatchRequest
from test.util import check_error_message

class TestBatchReferencesObject(unittest.TestCase):

    def batch_size_test(self, batch: ReferenceBatchRequest, expected_size: int):
        """
        Test each parameter to have the same expected size.

        Parameters
        ----------
        batch : ReferenceBatchRequest
            The reference batch.
        expected_size : int
            Expected size.
        """

        # test __len__
        self.assertEqual(len(batch), expected_size)

        # test _from_object_class_names
        self.assertEqual(len(batch._from_object_class_names), expected_size)

        # test _from_object_ids
        self.assertEqual(len(batch._from_object_ids), expected_size)

        # test _from_object_properties
        self.assertEqual(len(batch._from_object_properties), expected_size)

        # test _to_object_ids
        self.assertEqual(len(batch._to_object_ids), expected_size)

    def test_add_and___len__(self):
        """
        Test the `add` method.
        """

        batch = ReferenceBatchRequest()

        # invalid calls
        ## error messages
        type_error_message = 'All arguments must be of type string'

        with self.assertRaises(TypeError) as error:
            batch.add(10, "some_str", "some_str", "some_str")
        check_error_message(self, error, type_error_message)
        with self.assertRaises(TypeError) as error:
            batch.add("some_str", batch, "some_str", "some_str")
        check_error_message(self, error, type_error_message)
        with self.assertRaises(TypeError) as error:
            batch.add("some_str", "some_str", True, "some_str")
        check_error_message(self, error, type_error_message)
        with self.assertRaises(TypeError) as error:
            batch.add("some_str", "some_str", "some_str", 1.0)
        check_error_message(self, error, type_error_message)

        # valid calls
        ## test with a correctly formated URL
        batch = ReferenceBatchRequest()
        
        # test __len__
        self.batch_size_test(batch, 0)

        batch.add("04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                "Alpha",
                "a",
                "fc7eb129-f138-457f-b727-1b29db191a67",
                )
        self.batch_size_test(batch, 1)
        self.assertEqual(batch._from_object_ids[0], "04a4b17d-6beb-443a-b1bc-835b0dd4e660")
        self.assertEqual(batch._to_object_ids[0], "fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(batch._from_object_class_names[0], "Alpha")
        self.assertEqual(batch._from_object_properties[0], "a")


        batch.add("04a4b17d-6beb-443a-b1bc-835b0dd4e661",
                "Beta",
                "b",
                "fc7eb129-f138-457f-b727-1b29db191a68",
                )
        self.batch_size_test(batch, 2)
        # previously added reference
        self.assertEqual(batch._from_object_ids[0], "04a4b17d-6beb-443a-b1bc-835b0dd4e660")
        self.assertEqual(batch._to_object_ids[0], "fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(batch._from_object_class_names[0], "Alpha")
        self.assertEqual(batch._from_object_properties[0], "a")
        # currently added reference
        self.assertEqual(batch._from_object_ids[1], "04a4b17d-6beb-443a-b1bc-835b0dd4e661")
        self.assertEqual(batch._to_object_ids[1], "fc7eb129-f138-457f-b727-1b29db191a68")
        self.assertEqual(batch._from_object_class_names[1], "Beta")
        self.assertEqual(batch._from_object_properties[1], "b")

    
    def test_get_request_body(self):
        """
        Test the `get_request_body` method.
        """

        batch = ReferenceBatchRequest()

        # no references
        expected_return = []
        body = batch.get_request_body()
        self.assertEqual(body, expected_return)

        # add a reference
        batch.add("fd5af656-7d86-40da-9577-845c98e75543", "Griptape", "color",
                "1c51b14d-1652-4225-8dfc-7f4079616f65")
        body = batch.get_request_body()
        expected_return.append({
            "from": "weaviate://localhost/Griptape/fd5af656-7d86-40da-9577-845c98e75543/color",
            "to": "weaviate://localhost/1c51b14d-1652-4225-8dfc-7f4079616f65"
        })
        self.assertEqual(body, expected_return)

        # add another reference
        batch.add("fd5af656-7d86-40da-9577-845c98e75511", "Griptape", "length",
                "1c51b14d-1652-4225-8dfc-7f4079616f66")
        body = batch.get_request_body()
        expected_return.append({
            "from": "weaviate://localhost/Griptape/fd5af656-7d86-40da-9577-845c98e75511/length",
            "to": "weaviate://localhost/1c51b14d-1652-4225-8dfc-7f4079616f66"
        })
        self.assertEqual(body, expected_return)


class TestAddObjects(unittest.TestCase):

    def test_add_and___len__(self):
        """
        Test the `add` method.
        """

        batch = ObjectsBatchRequest()

        # invalid calls
        ## error messages
        data_type_error_message = "Object must be of type dict"
        class_type_error_message = "Class name must be of type str"

        # wrong data_object
        with self.assertRaises(TypeError) as error:
            batch.add(None, "Class")
        check_error_message(self, error, data_type_error_message)

        with self.assertRaises(TypeError) as error:
            batch.add(224345, "Class")
        check_error_message(self, error, data_type_error_message)

        # wrong class_name
        with self.assertRaises(TypeError) as error:
            batch.add({'name': 'Optimus Prime'}, None)
        check_error_message(self, error, class_type_error_message)

        with self.assertRaises(TypeError) as error:
            batch.add({'name': 'Optimus Prime'}, ["Transformer"])
        check_error_message(self, error, class_type_error_message)

        # valid calls
        self.assertEqual(len(batch), 0)
        expected_return = []

        # add an object without 'uuid' and 'vector'
        obj =  {
            'class': "Philosopher",
            'properties': {"name": "Socrates"}
        }
        expected_return.append({
            'class': "Philosopher",
            'properties': {"name": "Socrates"}
        })
        batch.add(obj['properties'], obj['class'])
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch._objects, expected_return)
        # change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch._objects, expected_return)

        # add an object without 'vector'
        obj =  {
            'class': "Chemist",
            'properties': {"name": "Marie Curie"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"
        }
        expected_return.append({
            'class': "Chemist",
            'properties': {"name": "Marie Curie"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"
        })
        batch.add(obj['properties'], obj['class'], obj['id'])
        self.assertEqual(len(batch), 2)
        self.assertEqual(batch._objects, expected_return)
        # change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch._objects, expected_return)

        # add an object without 'uuid'
        obj =  {
            'class': "Writer",
            'properties': {"name": "Stephen King"},
            'vector': [1, 2, 3]
        }
        expected_return.append({
            'class': "Writer",
            'properties': {"name": "Stephen King"},
            'vector': [1, 2, 3]
        })
        batch.add(obj['properties'], obj['class'], vector=obj['vector'])
        self.assertEqual(len(batch), 3)
        self.assertEqual(batch._objects, expected_return)
        # change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch._objects, expected_return)

        # add an object with all arguments
        obj =  {
            'class': "Inventor",
            'properties': {"name": "Nikola Tesla"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            'vector': [1, 2, 3]
        }
        expected_return.append({
            'class': "Inventor",
            'properties': {"name": "Nikola Tesla"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            'vector': [1, 2, 3]
        })
        batch.add(obj['properties'], obj['class'], obj['id'], obj['vector'])
        self.assertEqual(len(batch), 4)
        self.assertEqual(batch._objects, expected_return)
        # change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch._objects, expected_return)

    def test_get_request_body(self):
        """
        Test the `get_request_body` method.
        """

        batch = ObjectsBatchRequest()
        expected_return = []
        self.assertEqual(batch.get_request_body(), {"fields": ["ALL"], "objects": expected_return})

        # add an object without 'uuid' and 'vector'
        obj =  {
            'class': "Philosopher",
            'properties': {"name": "Socrates"}
        }
        expected_return.append({
            'class': "Philosopher",
            'properties': {"name": "Socrates"}
        })
        batch.add(obj['properties'], obj['class'])
        self.assertEqual(batch.get_request_body(), {"fields": ["ALL"], "objects": expected_return})

        # add an object without 'vector'
        obj =  {
            'class': "Chemist",
            'properties': {"name": "Marie Curie"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"
        }
        expected_return.append({
            'class': "Chemist",
            'properties': {"name": "Marie Curie"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"
        })
        batch.add(obj['properties'], obj['class'], obj['id'])
        self.assertEqual(batch.get_request_body(), {"fields": ["ALL"], "objects": expected_return})

        # add an object without 'uuid'
        obj =  {
            'class': "Writer",
            'properties': {"name": "Stephen King"},
            'vector': [1, 2, 3]
        }
        expected_return.append({
            'class': "Writer",
            'properties': {"name": "Stephen King"},
            'vector': [1, 2, 3]
        })
        batch.add(obj['properties'], obj['class'], vector=obj['vector'])
        self.assertEqual(batch.get_request_body(), {"fields": ["ALL"], "objects": expected_return})

        # add an object with all arguments
        obj =  {
            'class': "Inventor",
            'properties': {"name": "Nikola Tesla"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            'vector': [1, 2, 3]
        }
        expected_return.append({
            'class': "Inventor",
            'properties': {"name": "Nikola Tesla"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            'vector': [1, 2, 3]
        })
        batch.add(obj['properties'], obj['class'], obj['id'], obj['vector'])
        self.assertEqual(batch.get_request_body(), {"fields": ["ALL"], "objects": expected_return})

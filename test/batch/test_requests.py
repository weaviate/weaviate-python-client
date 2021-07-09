import unittest
from unittest.mock import patch
from weaviate import ReferenceBatchRequest, ObjectsBatchRequest
from test.util import check_error_message

class TestBatchReferencesObject(unittest.TestCase):

    @patch('weaviate.batch.requests.get_valid_uuid', side_effect=lambda x: x) 
    def test_add_and_get_request_body(self, mock_get_valid_uuid):
        """
        Test the `add` and the 'get_request_body' method.
        """

        batch = ReferenceBatchRequest()

        #######################################################################
        # invalid calls
        #######################################################################
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

        #######################################################################
        # valid calls
        #######################################################################
        batch = ReferenceBatchRequest()
        
        #######################################################################
        # test initial values
        self.assertEqual(batch.size, 0)
        self.assertEqual(len(batch._items), 0)
        self.assertEqual(mock_get_valid_uuid.call_count, 0)

        #######################################################################
        # add first reference
        batch.add(
            "Alpha",
            "UUID_1",
            "a",
            "UUID_2")
        self.assertEqual(batch.size, 1)
        self.assertEqual(len(batch._items), 1)
        expected_item_1 = {
            'from': 'weaviate://localhost/Alpha/UUID_1/a',
            'to': 'weaviate://localhost/UUID_2'
            }
        self.assertEqual(batch.get_request_body(), [expected_item_1])
        self.assertEqual(mock_get_valid_uuid.call_count, 2)

        #######################################################################
        # add second reference
        batch.add(
            "Beta",
            "UUID_2",
            "b",
            "UUID_3")
        self.assertEqual(batch.size, 2)
        self.assertEqual(len(batch._items), 2)
        expected_item_2 = {
            'from': 'weaviate://localhost/Beta/UUID_2/b',
            'to': 'weaviate://localhost/UUID_3'
            }
        self.assertEqual(batch.get_request_body(), [expected_item_1, expected_item_2])
        self.assertEqual(mock_get_valid_uuid.call_count, 4)


class TestAddObjects(unittest.TestCase):

    @patch('weaviate.batch.requests.get_vector', side_effect=lambda x: x) 
    @patch('weaviate.batch.requests.get_valid_uuid', side_effect=lambda x: x) 
    def test_add_and_get_request_body(self, mock_get_valid_uuid, mock_get_vector):
        """
        Test the `add` and the 'get_request_body' method.
        """

        batch = ObjectsBatchRequest()
        #######################################################################
        # invalid calls
        #######################################################################
        ## error messages
        data_type_error_message = "Object must be of type dict"
        class_type_error_message = "Class name must be of type str"

        #######################################################################
        # wrong data_object
        with self.assertRaises(TypeError) as error:
            batch.add("Class", None)
        check_error_message(self, error, data_type_error_message)

        with self.assertRaises(TypeError) as error:
            batch.add("Class", 224345)
        check_error_message(self, error, data_type_error_message)

        #######################################################################
        # wrong class_name
        with self.assertRaises(TypeError) as error:
            batch.add(None, {'name': 'Optimus Prime'})
        check_error_message(self, error, class_type_error_message)

        with self.assertRaises(TypeError) as error:
            batch.add(["Transformer"], {'name': 'Optimus Prime'})
        check_error_message(self, error, class_type_error_message)

        #######################################################################
        # valid calls
        #######################################################################
        ## test initial values
        self.assertEqual(batch.size, 0)
        self.assertEqual(len(batch._items), 0)
        self.assertEqual(mock_get_valid_uuid.call_count, 0)
        self.assertEqual(mock_get_vector.call_count, 0)
        expected_return = {
            "fields": [
                "ALL"
            ],
            "objects": []
        }
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object without 'uuid' and 'vector'
        obj =  {
            'class': "Philosopher",
            'properties': {"name": "Socrates"}
        }
        expected_return['objects'].append({
            'class': "Philosopher",
            'properties': {"name": "Socrates"}
        })
        batch.add(obj['class'], obj['properties'])
        self.assertEqual(batch.size, 1)
        self.assertEqual(len(batch._items), 1)
        self.assertEqual(mock_get_valid_uuid.call_count, 0)
        self.assertEqual(mock_get_vector.call_count, 0)
        self.assertEqual(batch.get_request_body(), expected_return)
        ## change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object without 'vector'
        obj =  {
            'class': "Chemist",
            'properties': {"name": "Marie Curie"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"
        }
        expected_return['objects'].append({
            'class': "Chemist",
            'properties': {"name": "Marie Curie"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"
        })
        batch.add(obj['class'], obj['properties'], obj['id'])
        self.assertEqual(batch.size, 2)
        self.assertEqual(len(batch._items), 2)
        self.assertEqual(mock_get_valid_uuid.call_count, 1)
        self.assertEqual(mock_get_vector.call_count, 0)
        self.assertEqual(batch.get_request_body(), expected_return)
        ## change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object without 'uuid'
        obj =  {
            'class': "Writer",
            'properties': {"name": "Stephen King"},
            'vector': [1, 2, 3]
        }
        expected_return['objects'].append({
            'class': "Writer",
            'properties': {"name": "Stephen King"},
            'vector': [1, 2, 3]
        })
        batch.add(obj['class'], obj['properties'], vector=obj['vector'])
        self.assertEqual(batch.size, 3)
        self.assertEqual(len(batch._items), 3)
        self.assertEqual(mock_get_valid_uuid.call_count, 1)
        self.assertEqual(mock_get_vector.call_count, 1)
        self.assertEqual(batch.get_request_body(), expected_return)
        ## change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object with all arguments
        obj =  {
            'class': "Inventor",
            'properties': {"name": "Nikola Tesla"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            'vector': [1, 2, 3]
        }
        expected_return['objects'].append({
            'class': "Inventor",
            'properties': {"name": "Nikola Tesla"},
            'id': "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            'vector': [1, 2, 3]
        })
        batch.add(obj['class'], obj['properties'], obj['id'], obj['vector'])
        self.assertEqual(batch.size, 4)
        self.assertEqual(len(batch._items), 4)
        self.assertEqual(mock_get_valid_uuid.call_count, 2)
        self.assertEqual(mock_get_vector.call_count, 2)
        self.assertEqual(batch.get_request_body(), expected_return)
        ## change obj and check if batch does not reflect this change
        obj['properties']['name'] = 'Test'
        self.assertEqual(batch.get_request_body(), expected_return)

"""
Test the 'weaviate.batch.requests' functions/classes.
"""
import unittest
from unittest.mock import patch

from test.util import check_error_message
from weaviate.batch.requests import ReferenceBatchRequest, ObjectsBatchRequest


class TestBatchReferences(unittest.TestCase):
    """
    Test the `ReferenceBatchRequest` class.
    """

    @patch("weaviate.batch.requests.get_valid_uuid", side_effect=lambda x: x)
    def test_add_and_get_request_body(self, mock_get_valid_uuid):
        """
        Test the all the ReferenceBatchRequest's methods.
        """

        batch = ReferenceBatchRequest()

        #######################################################################
        # invalid calls
        #######################################################################
        ## error messages
        type_error_message_1 = "'from_object_class_name' argument must be of type str"
        type_error_message_2 = "'from_property_name' argument must be of type str"
        type_error_message_3 = "'to_object_class_name' argument must be of type str"

        with self.assertRaises(TypeError) as error:
            batch.add(10, "some_str", "some_str", "some_str")
        check_error_message(self, error, type_error_message_1)

        with self.assertRaises(TypeError) as error:
            batch.add("some_str", "some_str", True, "some_str")
        check_error_message(self, error, type_error_message_2)

        with self.assertRaises(TypeError) as error:
            batch.add("some_str", "some_str", "some_str", "some_uuid", 1.0)
        check_error_message(self, error, type_error_message_3)

        #######################################################################
        # valid calls
        #######################################################################
        batch = ReferenceBatchRequest()

        #######################################################################
        # test initial values
        self.assertEqual(len(batch), 0)
        self.assertTrue(batch.is_empty())
        self.assertEqual(mock_get_valid_uuid.call_count, 0)

        #######################################################################
        # add first reference
        batch.add("Alpha", "UUID_1", "a", "UUID_2")
        self.assertEqual(len(batch), 1)
        self.assertFalse(batch.is_empty())
        expected_item_1 = {
            "from": "weaviate://localhost/Alpha/UUID_1/a",
            "to": "weaviate://localhost/UUID_2",
        }
        self.assertEqual(batch.get_request_body(), [expected_item_1])
        self.assertEqual(mock_get_valid_uuid.call_count, 2)

        #######################################################################
        # add second reference
        batch.add("Beta", "UUID_2", "b", "UUID_3")
        self.assertEqual(len(batch), 2)
        self.assertFalse(batch.is_empty())
        expected_item_2 = {
            "from": "weaviate://localhost/Beta/UUID_2/b",
            "to": "weaviate://localhost/UUID_3",
        }
        self.assertEqual(batch.get_request_body(), [expected_item_1, expected_item_2])
        self.assertEqual(mock_get_valid_uuid.call_count, 4)

        #######################################################################
        # pop first reference
        self.assertEqual(batch.pop(0), expected_item_1)
        self.assertEqual(len(batch), 1)

        #######################################################################
        # add one reference and pop it pop last reference
        batch.add("Beta", "UUID_3", "b", "UUID_4")
        expected_item_3 = {
            "from": "weaviate://localhost/Beta/UUID_3/b",
            "to": "weaviate://localhost/UUID_4",
        }
        self.assertEqual(len(batch), 2)
        self.assertFalse(batch.is_empty())
        self.assertEqual(batch.pop(), expected_item_3)
        self.assertEqual(len(batch), 1)
        self.assertFalse(batch.is_empty())

        #######################################################################
        # add 2 more references and then empty the batch
        batch.add("Beta", "UUID_4", "b", "UUID_5")
        batch.add("Beta", "UUID_5", "b", "UUID_4")
        self.assertEqual(len(batch), 3)
        self.assertFalse(batch.is_empty())
        batch.empty()
        self.assertEqual(len(batch), 0)
        self.assertTrue(batch.is_empty())


class TestBatchObjects(unittest.TestCase):
    """
    Test the `ObjectsBatchRequest` class.
    """

    @patch("weaviate.batch.requests.uuid4", side_effect=lambda: "d087b7c6a1155c898cb2f25bdeb9bf92")
    @patch("weaviate.batch.requests.get_vector", side_effect=lambda x: x)
    @patch("weaviate.batch.requests.get_valid_uuid", side_effect=lambda x: x)
    def test_add_and_get_request_body(self, mock_get_valid_uuid, mock_get_vector, mock_uuid4):
        """
        Test the all the ObjectsBatchRequest's methods.
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
            batch.add(
                data_object=None,
                class_name="Class",
            )
        check_error_message(self, error, data_type_error_message)

        with self.assertRaises(TypeError) as error:
            batch.add(
                data_object=224345,
                class_name="Class",
            )
        check_error_message(self, error, data_type_error_message)

        #######################################################################
        # wrong class_name
        with self.assertRaises(TypeError) as error:
            batch.add(
                data_object={"name": "Optimus Prime"},
                class_name=None,
            )
        check_error_message(self, error, class_type_error_message)

        with self.assertRaises(TypeError) as error:
            batch.add(
                data_object={"name": "Optimus Prime"},
                class_name=["Transformer"],
            )
        check_error_message(self, error, class_type_error_message)

        #######################################################################
        # valid calls
        #######################################################################
        ## test initial values
        self.assertEqual(len(batch), 0)
        self.assertTrue(batch.is_empty())
        self.assertEqual(mock_get_valid_uuid.call_count, 0)
        self.assertEqual(mock_get_vector.call_count, 0)
        expected_return = {"fields": ["ALL"], "objects": []}
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object without 'uuid' and 'vector'
        obj = {"class": "Philosopher", "properties": {"name": "Socrates"}}
        expected_return["objects"].append(
            {
                "class": "Philosopher",
                "properties": {"name": "Socrates"},
                "id": "d087b7c6a1155c898cb2f25bdeb9bf92",
            }
        )
        res_uuid = batch.add(
            data_object=obj["properties"],
            class_name=obj["class"],
        )
        self.assertEqual(len(batch), 1)
        self.assertFalse(batch.is_empty())
        self.assertEqual(mock_get_valid_uuid.call_count, 1)
        self.assertEqual(mock_get_vector.call_count, 0)
        self.assertEqual(batch.get_request_body(), expected_return)
        self.assertEqual(res_uuid, "d087b7c6a1155c898cb2f25bdeb9bf92")
        ## change obj and check if batch does not reflect this change
        obj["properties"]["name"] = "Test"
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object without 'vector'
        obj = {
            "class": "Chemist",
            "properties": {"name": "Marie Curie"},
            "id": "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
        }
        expected_return["objects"].append(
            {
                "class": "Chemist",
                "properties": {"name": "Marie Curie"},
                "id": "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93",
            }
        )
        res_uuid = batch.add(
            data_object=obj["properties"],
            class_name=obj["class"],
            uuid=obj["id"],
        )
        self.assertEqual(len(batch), 2)
        self.assertFalse(batch.is_empty())
        self.assertEqual(mock_get_valid_uuid.call_count, 2)
        self.assertEqual(mock_get_vector.call_count, 0)
        self.assertEqual(batch.get_request_body(), expected_return)
        self.assertEqual(res_uuid, "d087b7c6-a115-5c89-8cb2-f25bdeb9bf93")
        ## change obj and check if batch does not reflect this change
        obj["properties"]["name"] = "Test"
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object without 'uuid'
        obj = {"class": "Writer", "properties": {"name": "Stephen King"}, "vector": [1, 2, 3]}
        expected_return["objects"].append(
            {
                "class": "Writer",
                "properties": {"name": "Stephen King"},
                "vector": [1, 2, 3],
                "id": "d087b7c6a1155c898cb2f25bdeb9bf92",
            }
        )
        res_uuid = batch.add(
            data_object=obj["properties"],
            class_name=obj["class"],
            vector=obj["vector"],
        )
        self.assertEqual(len(batch), 3)
        self.assertFalse(batch.is_empty())
        self.assertEqual(mock_get_valid_uuid.call_count, 3)
        self.assertEqual(mock_get_vector.call_count, 1)
        self.assertEqual(batch.get_request_body(), expected_return)
        self.assertEqual(res_uuid, "d087b7c6a1155c898cb2f25bdeb9bf92")
        ## change obj and check if batch does not reflect this change
        obj["properties"]["name"] = "Test"
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # add an object with all arguments
        obj = {
            "class": "Inventor",
            "properties": {"name": "Nikola Tesla"},
            "id": "d087b7c6-a115-5c89-8cb2-f25bdeb9bf95",
            "vector": [1, 2, 3],
        }
        expected_return["objects"].append(
            {
                "class": "Inventor",
                "properties": {"name": "Nikola Tesla"},
                "id": "d087b7c6-a115-5c89-8cb2-f25bdeb9bf95",
                "vector": [1, 2, 3],
            }
        )
        res_uuid = batch.add(
            data_object=obj["properties"],
            class_name=obj["class"],
            uuid=obj["id"],
            vector=obj["vector"],
        )
        self.assertEqual(len(batch), 4)
        self.assertFalse(batch.is_empty())
        self.assertEqual(mock_get_valid_uuid.call_count, 4)
        self.assertEqual(mock_get_vector.call_count, 2)
        self.assertEqual(batch.get_request_body(), expected_return)
        self.assertEqual(res_uuid, "d087b7c6-a115-5c89-8cb2-f25bdeb9bf95")
        ## change obj and check if batch does not reflect this change
        obj["properties"]["name"] = "Test"
        self.assertEqual(batch.get_request_body(), expected_return)

        #######################################################################
        # pop one object with index=1

        self.assertEqual(batch.pop(0), expected_return["objects"][0])
        self.assertEqual(len(batch), 3)
        self.assertFalse(batch.is_empty())
        expected_return["objects"] = expected_return["objects"][1:]

        #######################################################################
        # pop last object

        self.assertEqual(batch.pop(), expected_return["objects"][-1])
        self.assertEqual(len(batch), 2)
        self.assertFalse(batch.is_empty())
        expected_return["objects"] = expected_return["objects"][:-1]

        #######################################################################
        # empty the batch request

        self.assertFalse(batch.is_empty())
        batch.empty()
        self.assertEqual(len(batch), 0)
        self.assertTrue(batch.is_empty())

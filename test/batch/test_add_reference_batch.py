import unittest
from unittest.mock import Mock
import requests
from weaviate import ReferenceBatchRequest, ObjectsBatchRequest, Client
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *

class TestBatchReferencesObject(unittest.TestCase):

    def batch_size_each_parameter(self, batch: ReferenceBatchRequest, expected_size: int):
        """
        Test each parameter to have the same expected size.

        Parameters
        ----------
        batch : ReferenceBatchRequest
            The reference batch.
        expected_size : int
            Expected size.
        """

        # test _from_object_class_names
        self.assertEqual(len(batch._from_object_class_names), expected_size)
        # test _from_object_ids
        self.assertEqual(len(batch._from_object_ids), expected_size)
        # test _from_object_properties
        self.assertEqual(len(batch._from_object_properties), expected_size)
        # test _to_object_ids
        self.assertEqual(len(batch._to_object_ids), expected_size)

    def test_ref_batch_size(self):
        """
        Test batch size.
        """

        batch = ReferenceBatchRequest()
        
        # Initialy it should have zero objects
        self.assertEqual(len(batch), 0)
        self.batch_size_each_parameter(batch, 0)

        # Add one reference
        batch.add("04a4b17d-6beb-443a-b1bc-835b0dd4e660", "Alpha", "a",
                "fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(len(batch), 1)
        self.batch_size_each_parameter(batch, 1)

        # Add another reference
        batch.add("not-an-uuid-1111-5dnd7dn", "Alpha", "a",
                "not-an-uuid-just-a-string")
        self.assertEqual(2, len(batch))
        self.batch_size_each_parameter(batch, 2)

        # Add another reference
        batch.add("000000000000000000000000", "1234", "ii",
                "000000000000000000000000")
        self.assertEqual(3, len(batch))
        self.batch_size_each_parameter(batch, 3)

    def test_ref_batch_added_values(self):
        """
        Test batch for correct added values.
        """

        # test with a correctly formated URL
        batch = ReferenceBatchRequest()
        batch.add("weaviate://localhost/04a4b17d-6beb-443a-b1bc-835b0dd4e660",
                "Alpha",
                "a",
                "weaviate://localhost/fc7eb129-f138-457f-b727-1b29db191a67",
                )
        self.assertEqual(batch._from_object_ids[0], "04a4b17d-6beb-443a-b1bc-835b0dd4e660")
        self.assertEqual(batch._to_object_ids[0], "fc7eb129-f138-457f-b727-1b29db191a67")
        self.assertEqual(batch._from_object_class_names[0], "Alpha")
        self.assertEqual(batch._from_object_properties[0], "a")

        # test with a incorrect formated url, should work nevertheless
        batch = ReferenceBatchRequest()
        batch.add("12345-1234",
                "Class/Alpha",
                "property_a",
                "this is not an uuid",
                )
        self.assertEqual(batch._from_object_ids[0], "12345-1234")
        self.assertEqual(batch._to_object_ids[0], "this is not an uuid")
        self.assertEqual(batch._from_object_class_names[0], "Class/Alpha")
        self.assertEqual(batch._from_object_properties[0], "property_a")

        # test with a incorrect formated url, should work nevertheless
        batch = ReferenceBatchRequest()
        batch.add("some_path/12345-1234",
                "Class/Alpha/",
                "//a/prop",
                "this_is_a_path//other_path/this is not an uuid",
                )
        self.assertEqual(batch._from_object_ids[0], "some_path/12345-1234")
        self.assertEqual(batch._to_object_ids[0], "this_is_a_path//other_path/this is not an uuid")
        self.assertEqual(batch._from_object_class_names[0], "Class/Alpha/")
        self.assertEqual(batch._from_object_properties[0], "//a/prop")

        # add another reference to the previous batch
        batch.add("http://this-is_diferent/Some_Path/12345-1234",
                "some_class",
                "some_prop",
                "www.path/////some_other_path/this is Not uuid",
                )
        self.assertEqual(batch._from_object_ids[0], "some_path/12345-1234")
        self.assertEqual(batch._to_object_ids[0], "this_is_a_path//other_path/this is not an uuid")
        self.assertEqual(batch._from_object_class_names[0], "Class/Alpha/")
        self.assertEqual(batch._from_object_properties[0], "//a/prop")

        self.assertEqual(batch._from_object_ids[1], "http://this-is_diferent/Some_Path/12345-1234")
        self.assertEqual(batch._to_object_ids[1], "www.path/////some_other_path/this is Not uuid")
        self.assertEqual(batch._from_object_class_names[1], "some_class")
        self.assertEqual(batch._from_object_properties[1], "some_prop")

    def test_ref_batch_add_reference(self):
        """
        Test batch get_request_body().
        """

        batch = ReferenceBatchRequest()

        # no references
        body = batch.get_request_body()
        self.assertIsInstance(body, list)
        self.assertFalse(body)

        # add a reference
        batch.add("fd5af656-7d86-40da-9577-845c98e75543", "Griptape", "color",
                "1c51b14d-1652-4225-8dfc-7f4079616f65")
        body = batch.get_request_body()
        self.assertIsInstance(body, list)
        self.assertTrue(body)
        self.assertIsInstance(body[0], dict)
        self.assertEqual(
            "weaviate://localhost/Griptape/fd5af656-7d86-40da-9577-845c98e75543/color",
            body[0]["from"])
        self.assertEqual(
            "weaviate://localhost/1c51b14d-1652-4225-8dfc-7f4079616f65",
            body[0]["to"])

        # add another reference
        batch.add("fd5af656-7d86-40da-9577-845c98e75511", "Griptape", "length",
                "1c51b14d-1652-4225-8dfc-7f4079616f66")
        body = batch.get_request_body()
        self.assertIsInstance(body, list)
        self.assertTrue(body)
        self.assertIsInstance(body[0], dict)
        self.assertIsInstance(body[1], dict)
        self.assertEqual(
            "weaviate://localhost/Griptape/fd5af656-7d86-40da-9577-845c98e75543/color",
            body[0]["from"])
        self.assertEqual(
            "weaviate://localhost/1c51b14d-1652-4225-8dfc-7f4079616f65",
            body[0]["to"])
        self.assertEqual(
            "weaviate://localhost/Griptape/fd5af656-7d86-40da-9577-845c98e75511/length",
            body[1]["from"])
        self.assertEqual(
            "weaviate://localhost/1c51b14d-1652-4225-8dfc-7f4079616f66",
            body[1]["to"])

    def test_ref_batch_exceptions(self):
        """
        Test batch raised exceptions.
        """

        batch = ReferenceBatchRequest()

        with self.assertRaises(TypeError):
            batch.add(10, "some_str", "some_str", "some_str")
        with self.assertRaises(TypeError):
            batch.add("some_str", batch, "some_str", "some_str")
        with self.assertRaises(TypeError):
            batch.add("some_str", "some_str", True, "some_str")
        with self.assertRaises(TypeError):
            batch.add("some_str", "some_str", "some_str", 1.0)

    def test_create_references_in_batch(self):
        """
        Test create references.
        """
        client = Client("http://test-add-references")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(client, connection_mock)

        
        batch = ReferenceBatchRequest()
        batch.add("431c13e7-7479-45ac-a956-29ef6c662a9e", "Product", "parts",
                            "1d5c8296-d24e-4e4b-b0e8-9e7e1b40bfb1")
        batch.add("715de36c-e528-47c2-a5ee-73cccadacbc0", "Product", "parts",
                            "465533f8-f0af-4f53-a51b-35a885423e6a")

        # with create_references
        client.batch.create_references(batch)
        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]
        
        self.assertEqual("/batch/references", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

        # with create
        client.batch.create(batch)
        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]

        self.assertEqual("/batch/references", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

    def test_create_references_batch_exceptions(self):
        """
        Test exceptions from create references.
        """
        client = Client("http://test-add-references")
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        replace_connection(client, connection_mock)

        batch = ReferenceBatchRequest()
        batch.add("431c13e7-7479-45ac-a956-29ef6c662a9e", "Product", "parts",
                            "1d5c8296-d24e-4e4b-b0e8-9e7e1b40bfb1")
        batch.add("715de36c-e528-47c2-a5ee-73cccadacbc0", "Product", "parts",
                            "465533f8-f0af-4f53-a51b-35a885423e6a")

        # test connection error
        with self.assertRaises(requests.exceptions.ConnectionError):
            client.batch.create(batch)
        ## test create for non batch object
        # with create_references
        with self.assertRaises(TypeError):
            client.batch.create_references([10., 20.])
        with self.assertRaises(TypeError):
            client.batch.create_references(ObjectsBatchRequest())
        # with create
        with self.assertRaises(TypeError):
            client.batch.create([10., 20.])



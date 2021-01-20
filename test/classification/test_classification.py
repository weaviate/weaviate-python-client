import unittest
from unittest.mock import patch, Mock
import requests
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.util import replace_connection, add_run_rest_to_mock, run_rest_raise_connection_error


class TestClassification(unittest.TestCase):

    def test_incomplete_builder_exceptions(self):
        """
        Test incomlete Builder.
        """
        client = weaviate.Client("http://weaviate:8080")
        
        # without any configuration
        with self.assertRaises(ValueError):
            client.classification.schedule()\
                .do()
        # without any required configuration
        with self.assertRaises(ValueError):
            client.classification.schedule()\
                .with_source_where_filter({})\
                .with_target_where_filter({})\
                .with_training_set_where_filter({})\
                .with_settings({})\
                .with_wait_for_completion()\
                .with_k(5)\
                .do()
        # with one required configuration
        with self.assertRaises(ValueError):
            client.classification.schedule()\
                .with_type("my_classification")\
                .do()
        # with two required configuration
        with self.assertRaises(ValueError):
            client.classification.schedule()\
                .with_type("my_classification")\
                .with_class_name("MyClass")\
                .do()
        # with three required configuration
        with self.assertRaises(ValueError):
            client.classification.schedule()\
                .with_type("my_classification")\
                .with_class_name("MyClass")\
                .with_based_on_properties(["prop1", "prop2"])\
                .do()
        # knn without k specified
        with self.assertRaises(ValueError):
            client.classification.schedule()\
                .with_type("knn")\
                .with_class_name("Europa")\
                .with_based_on_properties(["text"])\
                .with_classify_properties(["siblings"])\
                .do()

    def test_settings_type_exception(self):
        """
        Test for settings TypeError.
        """

        client = weaviate.Client("http://weaviate:8080")
        # wrong settings data type
        with self.assertRaises(TypeError):
            client.classification.schedule()\
                .with_type("my_classification")\
                .with_class_name("Europa")\
                .with_based_on_properties(["text"])\
                .with_classify_properties(["siblings"])\
                .with_settings([{'k' : 1}])\
                .do()

    def test_do_exceptions(self):
        """
        Test .do() method Exceptions.
        """

        client = weaviate.Client("http://weaviate:8080")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {}, 404)
        replace_connection(client, connection_mock)
        
        # test UnexpectedStatusCodeException for .do method
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            client.classification.schedule()\
                .with_type("my_classification")\
                .with_class_name("Europa")\
                .with_based_on_properties(["text"])\
                .with_classify_properties(["siblings"])\
                .do()

        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        replace_connection(client, connection_mock)

        with self.assertRaises(requests.exceptions.ConnectionError):
            client.classification.schedule()\
                .with_type("my_classification")\
                .with_class_name("Europa")\
                .with_based_on_properties(["text"])\
                .with_classify_properties(["siblings"])\
                .do()

    def test_get_exceptions(self):
        """
        Test .get(classification_uuid) method Exceptions.
        """

        client = weaviate.Client("http://weaviate:8080")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {}, 404)
        replace_connection(client, connection_mock)

        # test UnexpectedStatusCodeException for .get method
        with self.assertRaises(ValueError):
            client.classification.get("classification-uuid-420")
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            client.classification.get("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")

        connection_mock = Mock()  # Mock calling weaviate
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        replace_connection(client, connection_mock)

        with self.assertRaises(requests.exceptions.ConnectionError):
            client.classification.get("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")

    def test_builder_knn(self):
        """
        Test Builder kNN.
        """

        client = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {}, 201)
        replace_connection(client, connection_mock)

        client.classification.schedule()\
            .with_type("knn")\
            .with_class_name("Europa")\
            .with_based_on_properties(["text"])\
            .with_classify_properties(["siblings"])\
            .with_k(5)\
            .do()

        config = {
            "class": "Europa",
            "settings" : {
                "k": 5
            },
            "basedOnProperties": ["text"],
            "classifyProperties": ["siblings"],
            "type": "knn"
        }

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/classifications", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual(config, call_args[2])

    def test_is_complete(self):
        """
        Test the methd `is_complete`.
        """

        client = weaviate.Client("http://localhorst:8080")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {"status" : "completed"}, 200)
        replace_connection(client, connection_mock)

        self.assertTrue(client.classification.is_complete("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))
        self.assertFalse(client.classification.is_failed("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))
        self.assertFalse(client.classification.is_running("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))

    def test_is_failed(self):
        """
        Test the methd `is_failed`.
        """

        client = weaviate.Client("http://localhorst:8080")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {"status" : "failed"}, 200)
        replace_connection(client, connection_mock)

        self.assertFalse(client.classification.is_complete("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))
        self.assertTrue(client.classification.is_failed("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))
        self.assertFalse(client.classification.is_running("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))

    def test_is_running(self):
        """
        Test the methd `is_running`.
        """

        client = weaviate.Client("http://localhorst:8080")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {"status" : "running"}, 200)
        replace_connection(client, connection_mock)

        self.assertFalse(client.classification.is_complete("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))
        self.assertFalse(client.classification.is_failed("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))
        self.assertTrue(client.classification.is_running("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92"))

    def test_do(self):
        """
        Test the methd `is_running`.
        """

        client = weaviate.Client("http://localhorst:8080")
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {"id" : "Correct_id"}, 201)
        replace_connection(client, connection_mock)

        response =  client.classification.schedule()\
                .with_type("my_classification")\
                .with_class_name("Europa")\
                .with_based_on_properties(["text"])\
                .with_classify_properties(["siblings"])\
                .do()

        self.assertEqual(response, {"id" : "Correct_id"})

        with patch("weaviate.classification.classify.Classification.get") as mock_obj:
            mock_obj.return_value = {"id" : "Correct_id", "status" : "completed"}
            response =  client.classification.schedule()\
                    .with_type("my_classification")\
                    .with_class_name("Europa")\
                    .with_based_on_properties(["text"])\
                    .with_classify_properties(["siblings"])\
                    .with_wait_for_completion()\
                    .do()
            self.assertEqual(response, {"id" : "Correct_id", "status" : "completed"})

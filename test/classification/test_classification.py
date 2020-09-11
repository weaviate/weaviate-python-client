import unittest
import weaviate
from test.testing_util import replace_connection, add_run_rest_to_mock
from weaviate.connect import REST_METHOD_POST
from unittest.mock import Mock


class TestClassification(unittest.TestCase):

    def test_incomplete_builder(self):
        w = weaviate.Client("http://localhorst:8080")
        try:
            w.classification.schedule().do()
            self.fail("Expected error")
        except ValueError:
            pass
        try:
            # knn without k specified
            w.classification.schedule()\
                .with_type("knn")\
                .with_class_name("Europa")\
                .with_based_on_properties(["text"])\
                .with_classify_properties(["siblings"])\
                .do()
            self.fail("Expected error")
        except ValueError:
            pass

    def test_builder_knn(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {}, 201)
        replace_connection(w, connection_mock)

        w.classification.schedule()\
            .with_type("knn")\
            .with_class_name("Europa")\
            .with_based_on_properties(["text"])\
            .with_classify_properties(["siblings"])\
            .with_k(5)\
            .do()

        config = {
            "class": "Europa",
            "k": 5,
            "basedOnProperties": ["text"],
            "classifyProperties": ["siblings"],
            "type": "knn"
        }

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/classifications", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual(config, call_args[2])


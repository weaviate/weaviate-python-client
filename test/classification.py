import unittest
import weaviate
from test.testing_util import add_run_rest_to_mock
from weaviate.connect import REST_METHOD_POST
import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
else:
    from unittest.mock import Mock


class TestClassification(unittest.TestCase):

    def test_contextual_classification(self):
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        w.classification._connection = add_run_rest_to_mock(connection_mock, status_code=201, return_json={"classification": "result"})

        classify_class = "MyClass"
        based_on_prop = "prop"
        classify_prop = "label"
        payload = w.classification.get_contextual_config(classify_class, based_on_prop, classify_prop)

        result = w.classification.start(payload)
        self.assertEqual("result", result["classification"])
        connection_mock.run_rest.assert_called_with("/classifications", REST_METHOD_POST, payload)

    def test_knn_config(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.classification.get_knn_config(None, 1, "text", "spam")
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.classification.get_knn_config("Email", None, "text", "spam")
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.classification.get_knn_config("Email", 1, None, "spam")
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.classification.get_knn_config("Email", 1, "text", None)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.classification.get_knn_config("Email", 0, "text", "spam")
            self.fail("Wrong input accepted")
        except ValueError:
            pass

        config = w.classification.get_knn_config("Email", 7, "text", "spam")
        self.assertTrue("class" in config)
        self.assertTrue("k" in config)
        self.assertTrue("basedOnProperties" in config)
        self.assertTrue("classifyProperties" in config)
        self.assertTrue("type" in config)
        self.assertEqual(config["class"], "Email")
        self.assertEqual(config["k"], 7)
        self.assertEqual(config["basedOnProperties"], ["text"])
        self.assertEqual(config["classifyProperties"], ["spam"])
        self.assertEqual(config["type"], "knn")

    def test_contextual_config(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.classification.get_contextual_config(None, "context", "referenceToLabelClass")
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.classification.get_contextual_config("MyClass", None, "referenceToLabelClass")
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.classification.get_contextual_config("MyClass", "context", None)
            self.fail("Wrong input accepted")
        except TypeError:
            pass

        config = w.classification.get_contextual_config("Article", "content", "topic")
        self.assertTrue("class" in config)
        self.assertFalse("k" in config)
        self.assertTrue("basedOnProperties" in config)
        self.assertTrue("classifyProperties" in config)
        self.assertTrue("type" in config)
        self.assertEqual(config["class"], "Article")
        self.assertEqual(config["basedOnProperties"], ["content"])
        self.assertEqual(config["classifyProperties"], ["topic"])
        self.assertEqual(config["type"], "contextual")

    def test_add_filter(self):
        w = weaviate.Client("http://localhost:8080")
        unfiltered_config = w.classification.get_contextual_config("Class", "basedOn", "other")
        filter = {
            "operator": "Equal",
            "path": ["kind"],
            "valueString": "string"
        }

        new_config = w.classification.add_filter_to_config(weaviate.TRAINING_SET_WHERE_FILTER, filter, unfiltered_config)

        self.assertTrue("trainingSetWhere" in new_config)
        self.assertFalse("trainingSetWhere" in unfiltered_config)

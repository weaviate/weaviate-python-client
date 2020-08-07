import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *


class TestC11y(unittest.TestCase):

    def test_extend_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.contextionary.extend(None, "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", 1.0)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.contextionary.extend("lsd", None, 1.0)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.contextionary.extend("lsd", "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", None)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.contextionary.extend("lsd", "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", 1.1)
            self.fail("Wrong input accepted")
        except ValueError:
            pass
        try:
            w.contextionary.extend("lsd", "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", -1.0)
            self.fail("Wrong input accepted")
        except ValueError:
            pass

    def test_get_c11y_vector(self):
        w = weaviate.Client("http://citadelofricks.city:6969")
        connection_mock = Mock()
        connection_mock = add_run_rest_to_mock(connection_mock, return_json={"A": "B"})
        replace_connection(w, connection_mock)

        self.assertEqual("B", w.contextionary.get_concept_vector("sauce")["A"])

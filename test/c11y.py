import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *

class TestC11y(unittest.TestCase):

    def test_extend_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.extend_c11y(None, "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", 1.0)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.extend_c11y("lsd", None, 1.0)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.extend_c11y("lsd", "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", None)
            self.fail("Wrong input accepted")
        except TypeError:
            pass
        try:
            w.extend_c11y("lsd", "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", 1.1)
            self.fail("Wrong input accepted")
        except ValueError:
            pass
        try:
            w.extend_c11y("lsd", "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion", -1.0)
            self.fail("Wrong input accepted")
        except ValueError:
            pass
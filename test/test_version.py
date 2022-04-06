import unittest
import weaviate

class TestVersion(unittest.TestCase):

    def test_version(self):
        """
        Test the `__version__` global variable.
        """

        self.assertEqual(weaviate.__version__, "3.4.1", "Check if the version is set correctly!")

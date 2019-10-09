import unittest
from unittest.mock import Mock
import weaviate

class TestWeaviate(unittest.TestCase):
    def test_create_weaviate_object(self):
        try:
            w = weaviate.Weaviate("")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected
        #
        # try:
        #     w = weaviate.Weaviate("http://localhost:8080")
        # except Exception as e:
        #     self.fail("Unexpected exception: "+ str(e))

        # self.assertEqual(True, False)


if __name__ == '__main__':
    unittest.main()

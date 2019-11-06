import unittest
import weaviate

class TestIsReachable(unittest.TestCase):
    def test_no_weaviate_rachable(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            self.assertFalse(w.is_reachable())
        except Exception as e:
            self.fail("Should not end up in any exception: " +str(e))

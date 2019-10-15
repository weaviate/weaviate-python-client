import unittest
import weaviate

class TestWeaviate(unittest.TestCase):
    def test_create_weaviate_object_wrong_url(self):
        try:
            w = weaviate.Weaviate(None)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Weaviate(42)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Weaviate("")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected
        try:
            w = weaviate.Weaviate("hallo\tasdf")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected

    def test_create_weaviate_object_create_valid_object(self):
        try:
            w = weaviate.Weaviate("http://localhost:8080")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Weaviate("http://localhost:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Weaviate("http://test.domain/path:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))







if __name__ == '__main__':
    unittest.main()

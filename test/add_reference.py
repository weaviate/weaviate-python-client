import unittest
import weaviate


class TestAddReference(unittest.TestCase):
    def test_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.add_reference_to_thing(1, "prop", weaviate.SEMANTIC_TYPE_THINGS, "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.add_reference_to_thing("67972f90-1912-4464-af51-2e9a1b42f6d6", 1, weaviate.SEMANTIC_TYPE_THINGS, "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.add_reference_to_thing("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", 1, "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.add_reference_to_thing("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", weaviate.SEMANTIC_TYPE_THINGS, 1)
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.add_reference_to_thing("my UUID", "prop", weaviate.SEMANTIC_TYPE_THINGS, "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except ValueError:
            pass

        try:
            w.add_reference_to_thing("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", "thing", "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except ValueError:
            pass

        try:
            w.add_reference_to_thing("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", weaviate.SEMANTIC_TYPE_THINGS, "my uuid")
            self.fail("Expected to fail with error")
        except ValueError:
            pass
        #
        # try:
        #     w.add_reference_to_thing("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", weaviate.SEMANTIC_TYPE_THINGS, "7eacfab8-c803-46dd-8edf-47895303a796")
        #     self.fail("Expected to fail with error")
        # except :
        #     pass
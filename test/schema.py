import unittest
import weaviate
from unittest.mock import Mock

class MyTestCase(unittest.TestCase):
    def test_create_schema_invalid_input(self):
        w = weaviate.Weaviate("http://localhost:8080")
        try:
            w.create_schema(None)
            self.fail("No exception when no valid schema given")
        except ValueError:
            pass # Expected value error
        try:
            w.create_schema("/random/noFile")
            self.fail("No exception when no valid schema given")
        except ValueError:
            pass # Expected value error

        # self.assertEqual(True, False)

    def test_create_schema_load_file(self):
        w = weaviate.Weaviate("http://localhost:8080")
        connection_mock = Mock()
        w.connection = connection_mock
        w.create_schema("./schema_company.json")
        connection_mock.run_rest.assert_called()


if __name__ == '__main__':
    unittest.main()

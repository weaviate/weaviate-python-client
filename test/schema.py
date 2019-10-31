import unittest
import weaviate
from unittest.mock import Mock
from unittest.mock import patch
import copy
import os
from test.testing_util import add_run_rest_to_mock

company_test_schema = {
  "actions": {
    "classes": [],
    "type": "action"
  },
  "things": {
    "@context": "",
    "version": "0.2.0",
    "type": "thing",
    "name": "company",
    "maintainer": "yourfriends@weaviate.com",
    "classes": [
      {
        "class": "Company",
        "description": "A business that acts in the market",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name under which the company is known",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "legalBody",
            "description": "The legal body under which the company maintains its business",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "hasEmployee",
            "description": "The employees of the company",
            "dataType": [
              "Employee"
            ],
            "cardinality": "many",
            "keywords": []
          }
        ]
      },
      {
        "class": "Employee",
        "description": "An employee of the company",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name of the employee",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "job",
            "description": "the job description of the employee",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          },
          {
            "name": "yearsInTheCompany",
            "description": "The number of years this employee has worked in the company",
            "dataType": [
              "int"
            ],
            "cardinality": "atMostOne",
            "keywords": []
          }
        ]
      }
    ]
  }
}


class TestSchema(unittest.TestCase):
    def test_create_schema_invalid_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.create_schema(None)
            self.fail("No exception when no valid schema given")
        except TypeError:
            pass # Expected value error
        try:
            w.create_schema("/random/noFile")  # No valid file or url
            self.fail("No exception when no valid schema given")
        except ValueError:
            pass # Expected value error
        try:
            w.create_schema(42)  # No valid type
            self.fail("No exception when no valid schema given")
        except TypeError:
            pass # Expected value error
            # Load from URL

    # @patch('weaviate.client._get_dict_from_object')
    # def mock_get_dict_from_object(self, object_):
    #     return company_test_schema


    def test_create_schema_load_file(self):
        w = weaviate.Client("http://localhost:8080")

        # Load from URL
        with patch('weaviate.client._get_dict_from_object') as mock_util:
            # Mock weaviate.client._get_dict_from_object the function where
            # it is looked up see https://docs.python.org/3/library/unittest.mock.html#where-to-patch
            # for more information

            connection_mock_url = Mock()  # Mock weaviate.connection
            w.connection = connection_mock_url
            add_run_rest_to_mock(connection_mock_url)

            mock_util.return_value = company_test_schema

            w.create_schema("http://semi.technology/schema")
            mock_util.assert_called()
            connection_mock_url.run_rest.assert_called()


        # Load from file
        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file)
        w.connection = connection_mock_file  # Replace connection with mock

        current_dir = os.path.dirname(__file__)
        schema_json_file = os.path.join(current_dir, "schema_company.json")
        w.create_schema(schema_json_file)  # Load from file
        connection_mock_file.run_rest.assert_called()  # See if mock has been called

        # Load dict
        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        w.connection = connection_mock_dict
        w.create_schema(company_test_schema)
        connection_mock_dict.run_rest.assert_called()

        # Test schema missing actions/schema
        # Mock run_rest
        connection_mock = Mock()
        w.connection = add_run_rest_to_mock(connection_mock)
        schema = copy.deepcopy(company_test_schema)
        # Remove actions
        del schema[weaviate.client.SCHEMA_CLASS_TYPE_ACTIONS]
        w.create_schema(company_test_schema)

        schema = copy.deepcopy(company_test_schema)
        del schema[weaviate.client.SCHEMA_CLASS_TYPE_THINGS]
        w.create_schema(company_test_schema)
        connection_mock.run_rest.assert_called()

    def test_run_rest_failed(self):
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        w.connection = add_run_rest_to_mock(connection_mock, return_json={"Test error"}, status_code=500)

        try:
            w.create_schema(company_test_schema)
        except weaviate.UnexpectedStatusCodeException:
            pass  # Expected exception


if __name__ == '__main__':
    unittest.main()

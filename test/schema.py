import unittest
import weaviate

import copy
import os
from test.testing_util import add_run_rest_to_mock

import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
    from mock import patch
else:
    from unittest.mock import Mock
    from unittest.mock import patch


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

# A test schema as it was returned from a real weaviate instance
persons_return_test_schema = {
    "actions": {
        "classes": [],
        "type": "action"
    },
    "things": {
        "classes": [
            {
                "class": "Person",
                "description": "A person such as humans or personality known through culture",
                "properties": [
                    {
                        "cardinality": "atMostOne",
                        "dataType": [
                            "text"
                        ],
                        "description": "The name of this person",
                        "name": "name"
                    }
                ]
            },
            {
                "class": "Group",
                "description": "A set of persons who are associated with each other over some common properties",
                "properties": [
                    {
                        "cardinality": "atMostOne",
                        "dataType": [
                            "text"
                        ],
                        "description": "The name under which this group is known",
                        "name": "name"
                    },
                    {
                        "cardinality": "many",
                        "dataType": [
                            "Person"
                        ],
                        "description": "The persons that are part of this group",
                        "name": "members"
                    }
                ]
            }
        ],
        "type": "thing"
    }
}

# Schema containing explicit index
person_index_false_schema = {
  "actions": {
    "classes": [],
    "type": "action"
  },
  "things": {
    "@context": "",
    "version": "0.2.0",
    "type": "thing",
    "name": "people",
    "maintainer": "yourfriends@weaviate.com",
    "classes": [
      {
        "class": "Person",
        "description": "A person such as humans or personality known through culture",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name of this person",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
            "index": False
          }
        ]
      },
      {
        "class": "Group",
        "description": "A set of persons who are associated with each other over some common properties",
        "keywords": [],
        "properties": [
          {
            "name": "name",
            "description": "The name under which this group is known",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
            "index": True
          },
          {
            "name": "members",
            "description": "The persons that are part of this group",
            "dataType": [
              "Person"
            ],
            "cardinality": "many"
          }
        ]
      }
    ]
  }
}


stop_vectorization_schema = {
  "actions": {
    "classes": [],
    "type": "action"
  },
  "things": {
    "@context": "",
    "version": "0.2.0",
    "type": "thing",
    "name": "data",
    "maintainer": "yourfriends@weaviate.com",
    "classes": [
      {
        "class": "DataType",
        "description": "DataType",
        "keywords": [],
        "vectorizeClassName": False,
        "properties": [
          {
            "name": "owner",
            "description": "the owner",
            "dataType": [
              "text"
            ],
            "keywords": [],
            "vectorizePropertyName": False,
            "index": False
          },
          {
            "name": "complexDescription",
            "description": "Description of the complex type",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
            "vectorizePropertyName": False,
          },
          {
            "name": "hasPrimitives",
            "description": "The primitive data points",
            "dataType": [
              "Primitive"
            ],
            "cardinality": "many",
            "keywords": []
          }
        ]
      },

      {
        "class": "Primitive",
        "description": "DataType",
        "keywords": [],
        "vectorizeClassName": True,
        "properties": [
          {
            "name": "type",
            "description": "the primitive type",
            "dataType": [
              "text"
            ],
            "cardinality": "atMostOne",
            "keywords": [],
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
        with patch('weaviate._client_schema._get_dict_from_object') as mock_util:
            # Mock weaviate.client._get_dict_from_object the function where
            # it is looked up see https://docs.python.org/3/library/unittest.mock.html#where-to-patch
            # for more information

            connection_mock_url = Mock()  # Mock weaviate.connection
            w._connection = connection_mock_url
            add_run_rest_to_mock(connection_mock_url)

            mock_util.return_value = company_test_schema

            w.create_schema("http://semi.technology/schema")
            mock_util.assert_called()
            connection_mock_url.run_rest.assert_called()


        # Load from file
        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file)
        w._connection = connection_mock_file  # Replace connection with mock

        current_dir = os.path.dirname(__file__)
        schema_json_file = os.path.join(current_dir, "schema_company.json")
        w.create_schema(schema_json_file)  # Load from file
        connection_mock_file.run_rest.assert_called()  # See if mock has been called

        # Load dict
        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        w._connection = connection_mock_dict
        w.create_schema(company_test_schema)
        connection_mock_dict.run_rest.assert_called()

        # Test schema missing actions/schema
        # Mock run_rest
        connection_mock = Mock()
        w._connection = add_run_rest_to_mock(connection_mock)
        schema = copy.deepcopy(company_test_schema)
        # Remove actions
        del schema[weaviate.SEMANTIC_TYPE_ACTIONS]
        w.create_schema(company_test_schema)

        schema = copy.deepcopy(company_test_schema)
        del schema[weaviate.SEMANTIC_TYPE_THINGS]
        w.create_schema(company_test_schema)
        connection_mock.run_rest.assert_called()

    def test_run_rest_failed(self):
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        w._connection = add_run_rest_to_mock(connection_mock, return_json={"Test error"}, status_code=500)

        try:
            w.create_schema(company_test_schema)
        except weaviate.UnexpectedStatusCodeException:
            pass  # Expected exception

    def test_get_schema(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        w._connection = connection_mock_file  # Replace connection with mock

        schema = w.get_schema()
        connection_mock_file.run_rest.assert_called()  # See if mock has been called
        self.assertTrue("things" in schema)
        self.assertEqual(len(schema["things"]["classes"]), 2)

    def test_create_schema_with_explicit_index(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        w._connection = connection_mock_dict
        w.create_schema(person_index_false_schema)
        connection_mock_dict.run_rest.assert_called()

    def test_not_indexed_class_name(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        w._connection = connection_mock_dict
        w.create_schema(stop_vectorization_schema)
        connection_mock_dict.run_rest.assert_called()


    def test_invalid_schema(self):
        schema = {
            "class": "Category",
            "description": "Category an article is a type off",
            "properties": [
              {
                "cardinality": "atMostOne",
                "dataType": [
                  "text"
                ],
                "description": "category name",
                "name": "name"
              }
            ]
        }
        w = weaviate.Client("http://localhost:1234")
        try:
            w.create_schema(schema)
            self.fail("Expected SchemaValidationException")
        except weaviate.SchemaValidationException:
            pass


class TestContainsSchema(unittest.TestCase):

    def test_contains_a_schema(self):
        # If a schema is present it should return true otherwise false
        # 1. test schema is present:
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        w._connection = connection_mock_file  # Replace connection with mock

        self.assertTrue(w.contains_schema())

        # 2. test no schema is present:
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        empty_schema = {"actions":{"classes":[],"type":"action"},"things":{"classes":[],"type":"thing"}}
        add_run_rest_to_mock(connection_mock_file, empty_schema)
        w._connection = connection_mock_file  # Replace connection with mock

        self.assertFalse(w.contains_schema())

    def test_contains_specific_schema(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        w._connection = connection_mock_file  # Replace connection with mock
        self.assertFalse(w.contains_schema(company_test_schema))
        subset_schema = {
            "things": {
                "classes": [
                    {
                        "class": "Person",
                        "description": "",
                        "properties": [{
                                "cardinality": "atMostOne",
                                "dataType": ["text"],
                                "description": "",
                                "name": "name"
                            }
                        ]
                    }
                ]
            }
        }
        self.assertTrue(w.contains_schema(subset_schema))



if __name__ == '__main__':
    unittest.main()

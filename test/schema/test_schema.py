import unittest
import copy
import os
from unittest.mock import patch
import weaviate
from test.testing_util import replace_connection, add_run_rest_to_mock, Mock
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE, REST_METHOD_GET
from weaviate.exceptions import SchemaValidationException

company_test_schema = {
    "classes": 
    [
        {
            "class": "Company",
            "description": "A business that acts in the market",
            "properties": [
                {
                    "name": "name",
                    "description": "The name under which the company is known",
                    "dataType": ["text"],
                },
                {
                    "name": "legalBody",
                    "description": "The legal body under which the company maintains its business",
                    "dataType": ["text"],
                },
                {
                    "name": "hasEmployee",
                    "description": "The employees of the company",
                    "dataType": ["Employee"],
                }
            ]
        },
        {
            "class": "Employee",
            "description": "An employee of the company",
            "properties": [
                {
                    "name": "name",
                    "description": "The name of the employee",
                    "dataType": ["text"],
                },
                {
                    "name": "job",
                    "description": "the job description of the employee",
                    "dataType": ["text"],
                },
                {
                    "name": "yearsInTheCompany",
                    "description": "The number of years this employee has worked in the company",
                    "dataType": ["int"],
                }
            ]
        }
    ]
}

# A test schema as it was returned from a real weaviate instance
persons_return_test_schema = {
    "classes": [
        {
            "class": "Person",
            "description": "A person such as humans or personality known through culture",
            "properties": [
                {
                    "dataType": ["text"],
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
                    "dataType": ["text"],
                    "description": "The name under which this group is known",
                    "name": "name"
                },
                {
                    "dataType": ["Person"],
                    "description": "The persons that are part of this group",
                    "name": "members"
                }
            ]
        }
    ],
}

# Schema containing explicit index
person_index_false_schema = {
    "classes": [
        {
            "class": "Person",
            "description": "A person such as humans or personality known through culture",
            "properties": [
                {
                    "name": "name",
                    "description": "The name of this person",
                    "dataType": ["text"],
                    "indexInverted": False
                }
            ]
        },
        {
            "class": "Group",
            "description": "A set of persons who are associated with each other over some common properties",
            "properties": [
                {
                    "name": "name",
                    "description": "The name under which this group is known",
                    "dataType": ["text"],
                    "indexInverted": True
                },
                {
                    "name": "members",
                    "description": "The persons that are part of this group",
                    "dataType": ["Person"],
                }
            ]
        }
    ]
}

stop_vectorization_schema = {
    "classes": [
        {
            "class": "DataType",
            "description": "DataType",
            "moduleConfig": {
                "text2vec-contextionary": {  
                    "vectorizeClassName": False
                }
            },
            "properties": [
                {
                    "name": "owner",
                    "description": "the owner",
                    "dataType": ["text"],
                    "moduleConfig": {
                        "text2vec-contextionary": {  
                            "vectorizePropertyName": False
                        }
                    },
                    "indexInverted": False
                },
                {
                    "name": "complexDescription",
                    "description": "Description of the complex type",
                    "dataType": ["text"],
                    "moduleConfig": {
                        "text2vec-contextionary": {  
                            "vectorizePropertyName": False
                        }
                    }
                },
                {
                    "name": "hasPrimitives",
                    "description": "The primitive data points",
                    "dataType": ["Primitive"],
                }
            ]
        },
        {
            "class": "Primitive",
            "description": "DataType",
            "moduleConfig": {
                "text2vec-contextionary": {  
                    "vectorizeClassName": True
                }
            },
            "properties": [
                {
                    "name": "type",
                    "description": "the primitive type",
                    "dataType": ["text"],
                }
            ]
        }
    ]
}


class TestSchema(unittest.TestCase):

    def test_create_schema_invalid_input(self):
        """
        Test create schema exceptions.
        """

        client = weaviate.Client("http://localhost:8080")
		# None value
        with self.assertRaises(TypeError):
            client.schema.create(None)
		# invalid file
        with self.assertRaises(ValueError):
            client.schema.create("/random/noFile")
		# invalid url
        with self.assertRaises(ValueError):
            client.schema.create("https://www.semi.technology/schema")
		# wrong type
        with self.assertRaises(TypeError):
            client.schema.create(42)

    def test_create_schema_load_file(self):
        """
        Test create schema.
        """
        client = weaviate.Client("http://localhost:8080")
        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file)
        replace_connection(client, add_run_rest_to_mock(connection_mock_file))  # Replace connection with mock

        # Load from URL
        with patch('weaviate.schema.crud_schema._get_dict_from_object') as mock_util:
            mock_util.return_value = company_test_schema
            self.assertIsNone(client.schema.create("http://semi.technology/schema"))

        # Load from file
        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file)
        replace_connection(client, add_run_rest_to_mock(connection_mock_file))  # Replace connection with mock

        current_dir = os.path.dirname(__file__)
        schema_json_file = os.path.join(current_dir, "schema_company.json")
        client.schema.create(schema_json_file)  # Load from file
        connection_mock_file.run_rest.assert_called()  # See if mock has been called

        # Load dict
        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        replace_connection(client, add_run_rest_to_mock(connection_mock_dict))
        client.schema.create(company_test_schema)
        connection_mock_dict.run_rest.assert_called()

    def test_run_rest_failed(self):
        """
        test run_rest Failed.
        """

        client = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, return_json={"Test error"}, status_code=500)
        replace_connection(client, connection_mock)

        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            client.schema.create(company_test_schema)

    def test_get_schema(self):
        """
        Test schema.get
        """

        client = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(client, connection_mock_file)  # Replace connection with mock

        schema = client.schema.get()
        connection_mock_file.run_rest.assert_called()  # See if mock has been called
        self.assertTrue("classes" in schema)
        self.assertEqual(len(schema["classes"]), 2)

    def test_create_schema_with_explicit_index(self):
        """
        Test create schema with explicit indexInverted.
        """

        client = weaviate.Client("http://localhost:8080")

        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        replace_connection(client, connection_mock_dict)
        client.schema.create(person_index_false_schema)
        connection_mock_dict.run_rest.assert_called()

    def test_not_indexed_class_name(self):
        """
        Test un-indexed class name.
        """

        client = weaviate.Client("http://localhost:8080")

        connection_mock_dict = Mock()  # Replace mock
        add_run_rest_to_mock(connection_mock_dict)

        replace_connection(client, connection_mock_dict)
        client.schema.create(stop_vectorization_schema)
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
        client = weaviate.Client("http://localhost:1234")
        with self.assertRaises(weaviate.SchemaValidationException):
            client.schema.create(schema)


class TestContainsSchema(unittest.TestCase):

    def test_contains_a_schema(self):
        """
        Test weaviate.schema.contains any schema.
        """

        # If a schema is present it should return true otherwise false
        # 1. test schema is present:
        client = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(client, connection_mock_file)

        self.assertTrue(client.schema.contains())

        # 2. test no schema is present:
        client = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        empty_schema = {"classes": []}
        add_run_rest_to_mock(connection_mock_file, empty_schema)
        replace_connection(client, connection_mock_file)

        self.assertFalse(client.schema.contains())

    def test_contains_specific_schema(self):
        """
        Test weaviate.schema.contains specific schema.
        """

        client = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(client, connection_mock_file)
        self.assertFalse(client.schema.contains(company_test_schema))
        subset_schema = {
            "classes": [
                {
                    "class": "Person",
                    "description": "",
                    "properties": [
                        {
                            "dataType": ["text"],
                            "description": "",
                            "name": "name"
                        }
                    ]
                }
            ]
        }
        self.assertTrue(client.schema.contains(subset_schema))

    def test_contains_specific_schema_from_file(self):
        """
        Test weaviate.schema.contains schema from file.
        """

        client = weaviate.Client("http://localhost:8080")

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, persons_return_test_schema)
        replace_connection(client, connection_mock_file)

        current_dir = os.path.dirname(__file__)
        schema_json_file = os.path.join(current_dir, "schema_company.json")

        self.assertFalse(client.schema.contains(schema_json_file))

        connection_mock_file = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock_file, company_test_schema)
        replace_connection(client, connection_mock_file)

        self.assertTrue(client.schema.contains(schema_json_file))


class TestCreate(unittest.TestCase):

    def test_create_single_class(self):
        """
        Test create single class.
        """

        group_class = {
            "class": "Group",
            "description": "A set of persons who are associated with each other over some common properties",
            "properties": [
                {
                    "name": "name",
                    "description": "The name under which this group is known",
                    "dataType": ["text"],
                    "indexInverted": True
                },
                {
                    "name": "members",
                    "description": "The persons that are part of this group",
                    "dataType": ["Person"],
                }
            ]
        }

        client = weaviate.Client("http://localhost:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(client, connection_mock)

        self.assertIsNone(client.schema.create_class(group_class))

        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/schema", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        created_class = call_args[2]
        self.assertEqual("Group", created_class["class"])
        self.assertEqual(1, len(created_class["properties"]))

        call_args = call_args_list[1][0]
        self.assertEqual("/schema/Group/properties", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        created_property = call_args[2]
        self.assertEqual(["Person"], created_property["dataType"])


    def test_create_minimal_class(self):
        """
        Test create minimal class.
        """

        client = weaviate.Client("http://localhost:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(client, connection_mock)

        client.schema.create_class({"class": "Group"})

        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/schema", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual("Group", call_args[2]["class"])

    def test_input(self):
        """
        Test input.
        """

        client = weaviate.Client("http://localhorst:8080")
        invalid_class = {
            "class": "Group",
            "description": "A set of persons who are associated with each other over some common properties",
            "properties": [
                {
                    "name": "name",
                    "description": "The name under which this group is known",
                    "indexInverted": True
                },
                {
                    "name": "members",
                    "description": "The persons that are part of this group",
                    "dataType": [
                        "Person"
                    ],
                }
            ]
        }
        with self.assertRaises(SchemaValidationException):
            client.schema.create_class(invalid_class)


class TestDelete(unittest.TestCase):

    def test_delete_class_input(self):
        """
        Test delete class input exceptions.
        """
        client = weaviate.Client("http://localhost:8080")
        with self.assertRaises(TypeError):
            client.schema.delete_class(1)
        with self.assertRaises(TypeError):
            client.schema.delete_class("a", 1)

    def test_delete_class(self):
        """
        Test delete class.
        """

        client = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(client, connection_mock)

        self.assertIsNone(client.schema.delete_class("Poverty"))

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/schema/Poverty", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

    def test_delete_everything(self):
        """
        Test delete everything.
        """

        # First request get schema
        return_value_mock_get_schema = Mock()
        return_value_mock_get_schema.json.return_value = company_test_schema
        return_value_mock_get_schema.configure_mock(status_code=200)
        # Second request delete class 1
        return_value_mock_delete_class_1 = Mock()
        return_value_mock_delete_class_1.json.return_value = None
        return_value_mock_delete_class_1.configure_mock(status_code=200)
        # Third request delete class 2
        return_value_mock_delete_class_2 = Mock()
        return_value_mock_delete_class_2.json.return_value = None
        return_value_mock_delete_class_2.configure_mock(status_code=200)

        connection_mock = Mock()  # Mock calling weaviate
        #connection_mock.run_rest.return_value = [return_value_mock, return_value_mock2]
        connection_mock.run_rest.side_effect = [
            return_value_mock_get_schema,
            return_value_mock_delete_class_1,
            return_value_mock_delete_class_2]

        client = weaviate.Client("http://localhost:2121")
        replace_connection(client, connection_mock)

        client.schema.delete_all()

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        # Check if schema was retrieved
        call_args = call_args_list[0][0]

        self.assertEqual("/schema", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])

        # Check if class 1 was deleted
        call_args = call_args_list[1][0]

        self.assertEqual("/schema/Company", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

        # Check if class 2 was deleted
        call_args = call_args_list[2][0]

        self.assertEqual("/schema/Employee", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

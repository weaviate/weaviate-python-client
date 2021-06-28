import unittest
import copy
import os
from unittest.mock import patch, Mock
import weaviate
from test.util import replace_connection, mock_run_rest, check_error_message, check_startswith_error_message
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE, REST_METHOD_GET, REST_METHOD_PUT
from weaviate.exceptions import SchemaValidationException, RequestsConnectionError, UnexpectedStatusCodeException

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

schema_company_local = { # NOTE: should be the same as file schema_company.json
  "classes": [
    {
      "class": "Company",
      "description": "A business that acts in the market",
      "properties": [
        {
          "name": "name",
          "description": "The name under which the company is known",
          "dataType": ["text"]
        },
        {
          "name": "legalBody",
          "description": "The legal body under which the company maintains its business",
          "dataType": ["text"]
        },
        {
          "name": "hasEmployee",
          "description": "The employees of the company",
          "dataType": ["Employee"]
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
          "dataType": ["text"]
        },
        {
          "name": "job",
          "description": "the job description of the employee",
          "dataType": ["text"]
        },
        {
          "name": "yearsInTheCompany",
          "description": "The number of years this employee has worked in the company",
          "dataType": ["int"]
        }
      ]
    }
  ]
}

class TestSchema(unittest.TestCase):

    def setUp(self):
        
        self.client = weaviate.Client("http://localhost:8080")

    def test_create(self):
        """
        Test the `create` method.
        """

        # mock function calls
        mock_primitive = Mock()
        mock_complex = Mock()
        self.client.schema._create_classes_with_primitives = mock_primitive
        self.client.schema._create_complex_properties_from_classes = mock_complex

        self.client.schema.create("test/schema/schema_company.json") # with read from file

        mock_primitive.assert_called_with(schema_company_local["classes"])
        mock_complex.assert_called_with(schema_company_local["classes"])

    def test_create_class(self):
        """
        Test the `create_class` method.
        """

        # mock function calls
        mock_primitive = Mock()
        mock_complex = Mock()
        self.client.schema._create_class_with_premitives = mock_primitive
        self.client.schema._create_complex_properties_from_class = mock_complex

        self.client.schema.create_class(company_test_schema["classes"][0])

        mock_primitive.assert_called_with(company_test_schema["classes"][0])
        mock_complex.assert_called_with(company_test_schema["classes"][0])

    @patch('weaviate.schema.crud_schema.Schema.get')
    def test_update_config(self, mock_schema):
        """
        Test the `update_config` method.
        """

        # invalid calls
        requests_error_message = 'Test! Connection error, class schema configuration could not be updated.'
        unexpected_error_msg = 'Update class schema configuration'
        
        mock_schema.return_value = {'class': 'Test', 'vectorIndexConfig': {'test1': 'Test1', 'test2': 2}}
        mock_conn = mock_run_rest(side_effect=RequestsConnectionError("Test!"))
        replace_connection(self.client, mock_conn)
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.schema.update_config("Test", {'vectorIndexConfig': {'test2': 'Test2'}})
        check_error_message(self, error, requests_error_message)
        mock_conn.run_rest.assert_called_with("/schema/Test", REST_METHOD_PUT, {'class': 'Test', 'vectorIndexConfig': {'test1': 'Test1', 'test2': 'Test2'}})
        
        mock_schema.return_value = {'class': 'Test', 'vectorIndexConfig': {'test1': 'Test1', 'test2': 2}}
        mock_conn = mock_run_rest(status_code=404)
        replace_connection(self.client, mock_conn)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.schema.update_config("Test", {'vectorIndexConfig': {'test3': True}})
        check_startswith_error_message(self, error, unexpected_error_msg)
        mock_conn.run_rest.assert_called_with("/schema/Test", REST_METHOD_PUT, {'class': 'Test', 'vectorIndexConfig': {'test1': 'Test1', 'test2': 2, 'test3': True}})

        # valid calls
        mock_schema.return_value = {'class': 'Test', 'vectorIndexConfig': {'test1': 'Test1', 'test2': 2}}
        mock_conn = mock_run_rest()
        replace_connection(self.client, mock_conn)
        self.client.schema.update_config("Test", {})
        mock_conn.run_rest.assert_called_with("/schema/Test", REST_METHOD_PUT, {'class': 'Test', 'vectorIndexConfig': {'test1': 'Test1', 'test2': 2}})


    def test_get(self):
        """
        Test the `get` method.
        """

        # invalid calls
        requests_error_message = 'Test! Connection error, schema could not be retrieved.'
        unexpected_error_msg = "Get schema"
        type_error_msg = lambda dt: f"'class_name' argument must be of type `str`! Given type: {dt}"

        mock_conn = mock_run_rest(side_effect=RequestsConnectionError("Test!"))
        replace_connection(self.client, mock_conn)
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.schema.get()
        check_error_message(self, error, requests_error_message)

        mock_conn = mock_run_rest(status_code=404)
        replace_connection(self.client, mock_conn)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.schema.get()
        check_startswith_error_message(self, error, unexpected_error_msg)

        connection_mock_file = mock_run_rest(status_code=200, return_json={'Test': 'OK!'})
        replace_connection(self.client, connection_mock_file)  # Replace connection with mock
        with self.assertRaises(TypeError) as error:
            self.client.schema.get(1234)
        check_error_message(self, error, type_error_msg(int))

        # valid calls

        self.assertEqual(self.client.schema.get(), {'Test': 'OK!'})
        connection_mock_file.run_rest.assert_called_with("/schema", REST_METHOD_GET)  # See if mock has been called

        self.assertEqual(self.client.schema.get("Artist"), {'Test': 'OK!'})
        connection_mock_file.run_rest.assert_called_with("/schema/Artist", REST_METHOD_GET)  # See if mock has been called

    def test_contains(self):
        """
        Test the `contains` method.
        """

        # If a schema is present it should return true otherwise false
        # 1. test schema is present:

        replace_connection(self.client, mock_run_rest(return_json=persons_return_test_schema))
        self.assertTrue(self.client.schema.contains())

        # 2. test no schema is present:

        replace_connection(self.client, mock_run_rest(return_json={"classes": []}))
        self.assertFalse(self.client.schema.contains())

        # 3. test with 'schema' argument
        ## Test weaviate.schema.contains specific schema.
    
        replace_connection(self.client, mock_run_rest(return_json=persons_return_test_schema))
        self.assertFalse(self.client.schema.contains(company_test_schema))
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
        self.assertTrue(self.client.schema.contains(subset_schema))

        ## Test weaviate.schema.contains schema from file.

        replace_connection(self.client, mock_run_rest(return_json=persons_return_test_schema))
        schema_json_file = os.path.join(os.path.dirname(__file__), "schema_company.json")
        self.assertFalse(self.client.schema.contains(schema_json_file))

        replace_connection(self.client, mock_run_rest(return_json=company_test_schema))
        self.assertTrue(self.client.schema.contains(schema_json_file))

    def test_delete_class_input(self):
        """
        Test the 'delete_class` method.
        """

        # invalid calls
        type_error_message = lambda t: f"Class name was {t} instead of str"
        requests_error_message = 'Test! Connection error, during deletion of class.'

        with self.assertRaises(TypeError) as error:
            self.client.schema.delete_class(1)
        check_error_message(self, error, type_error_message(int))

        replace_connection(self.client, mock_run_rest(side_effect=RequestsConnectionError('Test!')))
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.schema.delete_class("uuid")
        check_error_message(self, error, requests_error_message)

        replace_connection(self.client, mock_run_rest(status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.schema.delete_class("uuid")
        check_startswith_error_message(self, error, "Delete class from schema")

        # valid calls
        mock_conn = mock_run_rest(status_code=200)
        replace_connection(self.client, mock_conn)
        self.client.schema.delete_class("uuid")
        mock_conn.run_rest.assert_called_with("/schema/uuid", REST_METHOD_DELETE)


    def test_delete_everything(self):
        """
        Test the `delete_all` method.
        """

        mock_get = mock_run_rest(return_json=company_test_schema)
        replace_connection(self.client, mock_get)

        self.client.schema.delete_all()
        self.assertEqual(mock_get.run_rest.call_count, 2 + 1) # + 1 is for the getting the schema

    def test__create_complex_properties_from_classes(self):
        """
        Test the `_create_complex_properties_from_classes` method.
        """

        mock_complex = Mock()
        self.client.schema._create_complex_properties_from_class = mock_complex

        self.client.schema._create_complex_properties_from_classes(list("Test!"))
        self.assertEqual(mock_complex.call_count, 5)

    def test__create_complex_properties_from_class(self):
        """
        Test the `_create_complex_properties_from_class` method.
        """
        
        # valid calls
        test_func = self.client.schema._create_complex_properties_from_class

        def helper_test(nr_calls=1):
            mock_rest = mock_run_rest()
            replace_connection(self.client, mock_rest)
            test_func(properties)
            self.assertEqual(mock_rest.run_rest.call_count, nr_calls)
            mock_rest.run_rest.assert_called_with(
                "/schema/" + properties["class"] + "/properties",
                REST_METHOD_POST,
                properties['properties'][0])

        # no `properties` key
        mock_rest = mock_run_rest()
        replace_connection(self.client, mock_rest)
        test_func({})
        self.assertEqual(mock_rest.run_rest.call_count, 0)

        # no COMPLEX properties
        properties = {
            'properties':[
                {'dataType': ["text"]}
            ]
        }
        test_func(properties)
        self.assertEqual(mock_rest.run_rest.call_count, 0)

        properties = {
            'properties':[
                {'dataType': ["text"]},
                {'dataType': ['string']}
            ]
        }
        test_func(properties)
        self.assertEqual(mock_rest.run_rest.call_count, 0)

        properties = {
            'class' : 'TestClass',
            'properties':[
                {
                    'dataType': ["Test"],
                    'description': "test description",
                    'name': 'test_prop'
                },
                
            ]
        }
        mock_rest = mock_run_rest()
        replace_connection(self.client, mock_rest)
        test_func(properties)
        self.assertEqual(mock_rest.run_rest.call_count, 1)

        properties = {
            'class' : 'TestClass',
            'properties':[
                {
                    'dataType': ["Test"],
                    'description': "test description",
                    'name': 'test_prop'
                },
                
            ]
        }
        helper_test()

        properties['properties'][0]['indexInverted'] = True
        helper_test()

        properties['properties'][0]['moduleConfig'] = {'test': 'ok!'}
        helper_test()
        
        properties['properties'].append(properties['properties'][0]) # add another property
        properties['properties'].append(properties['properties'][0]) # add another property
        helper_test(3)

        # invalid calls
        requests_error_message = 'TEST1 Connection error, property may not have been created properly.'

        mock_rest = mock_run_rest(side_effect=RequestsConnectionError('TEST1'))
        replace_connection(self.client, mock_rest)
        with self.assertRaises(RequestsConnectionError) as error:
            test_func(properties)
        check_error_message(self, error, requests_error_message)

        mock_rest = mock_run_rest(status_code=404)
        replace_connection(self.client, mock_rest)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            test_func(properties)
        check_startswith_error_message(self, error, "Add properties to classes")

    def test__create_class_with_premitives(self):
        """
        Test the `_create_class_with_premitives` method.
        """
        
        # valid calls
        test_func = self.client.schema._create_class_with_premitives
        def helper_test():
            mock_rest = mock_run_rest()
            replace_connection(self.client, mock_rest)
            test_func(test_class)
            self.assertEqual(mock_rest.run_rest.call_count, 1)
            mock_rest.run_rest.assert_called_with(
                "/schema",
                REST_METHOD_POST,
                test_class_call)

        test_class = {
            "class": "TestClass",
            "properties": [
                {
                    'dataType': ['int'],
                    'name': 'test_prop',
                    'description': 'None'
                },
                {
                    'dataType': ['Test'],
                    'name': 'test_prop',
                    'description': 'None'
                }
            ]
        }
        test_class_call = {
            "class": "TestClass",
            "properties": [
                {
                    'dataType': ['int'],
                    'name': 'test_prop',
                    'description': 'None'
                },
            ]
        }
        helper_test()

        test_class['description'] = 'description'
        test_class_call['description'] = 'description'
        helper_test()
        
        test_class['description'] = 'description'
        test_class_call['description'] = 'description'
        helper_test()

        test_class['vectorIndexType'] = 'vectorIndexType'
        test_class_call['vectorIndexType'] = 'vectorIndexType'
        helper_test()

        test_class['vectorIndexConfig'] = {'vectorIndexConfig': 'vectorIndexConfig'}
        test_class_call['vectorIndexConfig'] = {'vectorIndexConfig': 'vectorIndexConfig'}
        helper_test()

        test_class['vectorizer'] = 'test_vectorizer'
        test_class_call['vectorizer'] = 'test_vectorizer'
        helper_test()

        test_class['moduleConfig'] = {'moduleConfig': 'moduleConfig'}
        test_class_call['moduleConfig'] = {'moduleConfig': 'moduleConfig'}
        helper_test()

        # multiple properties do not imply multimple `run_rest` calls
        test_class['properties'].append(test_class['properties'][0]) # add another property
        test_class['properties'].append(test_class['properties'][0]) # add another property
        test_class_call['properties'].append(test_class['properties'][0]) # add another property
        test_class_call['properties'].append(test_class['properties'][0]) # add another property
        helper_test()

        

        # invalid calls
        requests_error_message = 'TEST1 Connection error, class may not have been created properly.'

        mock_rest = mock_run_rest(side_effect=RequestsConnectionError('TEST1'))
        replace_connection(self.client, mock_rest)
        with self.assertRaises(RequestsConnectionError) as error:
            test_func(test_class)
        check_error_message(self, error, requests_error_message)

        mock_rest = mock_run_rest(status_code=404)
        replace_connection(self.client, mock_rest)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            test_func(test_class)
        check_startswith_error_message(self, error, "Create class")

    def test__create_classes_with_primitives(self):
        """
        Test the `_create_classes_with_primitives` method.
        """

        mock_primitive = Mock()
        self.client.schema._create_class_with_premitives = mock_primitive

        self.client.schema._create_classes_with_primitives(list("Test!!"))
        self.assertEqual(mock_primitive.call_count, 6) 

    def test__property_is_primitive(self):
        """
        Test the `_property_is_primitive` function.
        """

        test_types_list = ["NOT Primitive", "Neither this one", "Nor This!"]
        self.assertFalse(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["NOT Primitive", "boolean", "text"]
        self.assertFalse(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["text"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["int"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["number"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["string"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["boolean"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["date"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["geoCoordinates"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["blob"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))
        test_types_list = ["string", "int", "boolean", "number", "date", "text", "geoCoordinates", "blob"]
        self.assertTrue(weaviate.schema.crud_schema._property_is_primitive(test_types_list))

    def test__get_primitive_properties(self):
        """
        Test the `_get_primitive_properties` function.
        """

        test_func = weaviate.schema.crud_schema._get_primitive_properties

        properties_list = []
        self.assertEqual(test_func(properties_list), properties_list)

        properties_list = [{'dataType': ["text"]}]
        self.assertEqual(test_func(properties_list), properties_list)

        properties_list = [{'dataType': ["text"]}, {'dataType': ["int"]}]
        self.assertEqual(test_func(properties_list), properties_list)

        properties_list = [{'dataType': ["Test1"]}, {'dataType': ["Test2"]}]
        self.assertEqual(test_func(properties_list), [])

        properties_list = [{'dataType': ["text"]}, {'dataType': ["int"]}, {'dataType': ["Test1"]}, {'dataType': ["Test2"]}]
        self.assertEqual(test_func(properties_list), [{'dataType': ["text"]}, {'dataType': ["int"]}])

import os
import unittest
from copy import deepcopy
from unittest.mock import patch, Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.schema import Schema
from weaviate.util import _capitalize_first_letter

company_test_schema = {
    "classes": [
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
                },
            ],
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
                },
            ],
        },
    ]
}

# A test schema as it was returned from a real weaviate instance
persons_return_test_schema = {
    "classes": [
        {
            "class": "Person",
            "description": "A person such as humans or personality known through culture",
            "properties": [
                {"dataType": ["text"], "description": "The name of this person", "name": "name"}
            ],
        },
        {
            "class": "Group",
            "description": "A set of persons who are associated with each other over some common properties",
            "properties": [
                {
                    "dataType": ["text"],
                    "description": "The name under which this group is known",
                    "name": "name",
                },
                {
                    "dataType": ["Person"],
                    "description": "The persons that are part of this group",
                    "name": "members",
                },
            ],
        },
    ],
}

schema_company_local = {  # NOTE: should be the same as file schema_company.json
    "classes": [
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
                },
            ],
        },
        {
            "class": "Employee",
            "description": "An employee of the company",
            "properties": [
                {"name": "name", "description": "The name of the employee", "dataType": ["text"]},
                {
                    "name": "job",
                    "description": "the job description of the employee",
                    "dataType": ["text"],
                },
                {
                    "name": "yearsInTheCompany",
                    "description": "The number of years this employee has worked in the company",
                    "dataType": ["int"],
                },
            ],
        },
    ]
}


class TestSchema(unittest.TestCase):
    def test_create(self):
        """
        Test the `create` method.
        """

        schema = Schema(Mock())

        # mock function calls
        mock_primitive = Mock()
        mock_complex = Mock()
        schema._create_classes_with_primitives = mock_primitive
        schema._create_complex_properties_from_classes = mock_complex

        schema.create("test/schema/schema_company.json")  # with read from file

        mock_primitive.assert_called_with(schema_company_local["classes"])
        mock_complex.assert_called_with(schema_company_local["classes"])

    def test_create_class(self):
        """
        Test the `create_class` method.
        """

        schema = Schema(Mock())

        # mock function calls
        mock_primitive = Mock()
        mock_complex = Mock()
        schema._create_class_with_primitives = mock_primitive
        schema._create_complex_properties_from_class = mock_complex

        schema.create_class(company_test_schema["classes"][0])

        mock_primitive.assert_called_with(company_test_schema["classes"][0])
        mock_complex.assert_called_with(company_test_schema["classes"][0])

    @patch("weaviate.schema.crud_schema.Schema.get")
    def test_update_config(self, mock_schema):
        """
        Test the `update_config` method.
        """

        # invalid calls
        requests_error_message = "Class schema configuration could not be updated."
        unexpected_error_msg = "Update class schema configuration"

        mock_schema.return_value = {
            "class": "Test",
            "vectorIndexConfig": {"test1": "Test1", "test2": 2},
        }
        mock_conn = mock_connection_func("put", side_effect=RequestsConnectionError("Test!"))
        schema = Schema(mock_conn)
        with self.assertRaises(RequestsConnectionError) as error:
            schema.update_config("Test", {"vectorIndexConfig": {"test2": "Test2"}})
        check_error_message(self, error, requests_error_message)
        mock_conn.put.assert_called_with(
            path="/schema/Test",
            weaviate_object={
                "class": "Test",
                "vectorIndexConfig": {"test1": "Test1", "test2": "Test2"},
            },
        )

        mock_schema.return_value = {
            "class": "Test",
            "vectorIndexConfig": {"test1": "Test1", "test2": 2},
        }
        mock_conn = mock_connection_func("put", status_code=404)
        schema = Schema(mock_conn)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            schema.update_config("Test", {"vectorIndexConfig": {"test3": True}})
        check_startswith_error_message(self, error, unexpected_error_msg)
        mock_conn.put.assert_called_with(
            path="/schema/Test",
            weaviate_object={
                "class": "Test",
                "vectorIndexConfig": {"test1": "Test1", "test2": 2, "test3": True},
            },
        )

        # valid calls
        mock_schema.return_value = {
            "class": "Test",
            "vectorIndexConfig": {"test1": "Test1", "test2": 2},
        }
        mock_conn = mock_connection_func("put")
        schema = Schema(mock_conn)
        schema.update_config("Test", {})
        mock_conn.put.assert_called_with(
            path="/schema/Test",
            weaviate_object={"class": "Test", "vectorIndexConfig": {"test1": "Test1", "test2": 2}},
        )

        # with uncapitalized class_name
        mock_schema.return_value = {
            "class": "Test",
            "vectorIndexConfig": {"test1": "Test1", "test2": 2},
        }
        mock_conn = mock_connection_func("put")
        schema = Schema(mock_conn)
        schema.update_config("test", {})
        mock_conn.put.assert_called_with(
            path="/schema/Test",
            weaviate_object={"class": "Test", "vectorIndexConfig": {"test1": "Test1", "test2": 2}},
        )

    def test_get(self):
        """
        Test the `get` method.
        """

        # invalid calls
        requests_error_message = "Schema could not be retrieved."
        unexpected_error_msg = "Get schema"
        type_error_msg = lambda dt: f"'class_name' argument must be of type `str`! Given type: {dt}"

        mock_conn = mock_connection_func("get", side_effect=RequestsConnectionError("Test!"))
        schema = Schema(mock_conn)
        with self.assertRaises(RequestsConnectionError) as error:
            schema.get()
        check_error_message(self, error, requests_error_message)

        mock_conn = mock_connection_func("get", status_code=404)
        schema = Schema(mock_conn)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            schema.get()
        check_startswith_error_message(self, error, unexpected_error_msg)

        connection_mock_file = mock_connection_func(
            "get", status_code=200, return_json={"Test": "OK!"}
        )
        schema = Schema(connection_mock_file)
        with self.assertRaises(TypeError) as error:
            schema.get(1234)
        check_error_message(self, error, type_error_msg(int))

        # valid calls

        self.assertEqual(schema.get(), {"Test": "OK!"})
        connection_mock_file.get.assert_called_with(
            path="/schema",
        )

        self.assertEqual(schema.get("Artist"), {"Test": "OK!"})
        connection_mock_file.get.assert_called_with(path="/schema/Artist")

        # with uncapitalized class_name
        self.assertEqual(schema.get("artist"), {"Test": "OK!"})
        connection_mock_file.get.assert_called_with(path="/schema/Artist")

    def test_contains(self):
        """
        Test the `contains` method.
        """

        # If a schema is present it should return true otherwise false
        # 1. test schema is present:

        schema = Schema(mock_connection_func("get", return_json=persons_return_test_schema))
        self.assertTrue(schema.contains())

        # 2. test no schema is present:

        schema = Schema(mock_connection_func("get", return_json={"classes": []}))
        self.assertFalse(schema.contains())

        # 3. test with 'schema' argument
        ## Test weaviate.schema.contains specific schema.

        schema = Schema(mock_connection_func("get", return_json=persons_return_test_schema))
        self.assertFalse(schema.contains(company_test_schema))
        subset_schema = {
            "classes": [
                {
                    "class": "Person",
                    "description": "",
                    "properties": [{"dataType": ["text"], "description": "", "name": "name"}],
                }
            ]
        }
        self.assertTrue(schema.contains(subset_schema))

        ## Test weaviate.schema.contains schema from file.

        schema = Schema(mock_connection_func("get", return_json=persons_return_test_schema))
        schema_json_file = os.path.join(os.path.dirname(__file__), "schema_company.json")
        self.assertFalse(schema.contains(schema_json_file))

        schema = Schema(mock_connection_func("get", return_json=company_test_schema))
        self.assertTrue(schema.contains(schema_json_file))

    def test_delete_class_input(self):
        """
        Test the 'delete_class` method.
        """

        schema = Schema(Mock())

        # invalid calls
        type_error_message = lambda t: f"Class name was {t} instead of str"
        requests_error_message = "Deletion of class."

        with self.assertRaises(TypeError) as error:
            schema.delete_class(1)
        check_error_message(self, error, type_error_message(int))

        schema = Schema(
            mock_connection_func("delete", side_effect=RequestsConnectionError("Test!"))
        )
        with self.assertRaises(RequestsConnectionError) as error:
            schema.delete_class("uuid")
        check_error_message(self, error, requests_error_message)

        schema = Schema(mock_connection_func("delete", status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            schema.delete_class("uuid")
        check_startswith_error_message(self, error, "Delete class from schema")

        # valid calls
        mock_conn = mock_connection_func("delete", status_code=200)
        schema = Schema(mock_conn)
        schema.delete_class("Test")
        mock_conn.delete.assert_called_with(path="/schema/Test")

        # with uncapitalized class_name
        mock_conn = mock_connection_func("delete", status_code=200)
        schema = Schema(mock_conn)
        schema.delete_class("test")
        mock_conn.delete.assert_called_with(path="/schema/Test")

    def test_delete_everything(self):
        """
        Test the `delete_all` method.
        """

        mock_connection = mock_connection_func("get", return_json=company_test_schema)
        mock_connection = mock_connection_func("delete", connection_mock=mock_connection)
        schema = Schema(mock_connection)

        schema.delete_all()
        self.assertEqual(mock_connection.get.call_count, 1)
        self.assertEqual(mock_connection.delete.call_count, 2)

    def test__create_complex_properties_from_classes(self):
        """
        Test the `_create_complex_properties_from_classes` method.
        """

        schema = Schema(Mock())

        mock_complex = Mock()
        schema._create_complex_properties_from_class = mock_complex

        schema._create_complex_properties_from_classes(list("Test!"))
        self.assertEqual(mock_complex.call_count, 5)

    def test__create_complex_properties_from_class(self):
        """
        Test the `_create_complex_properties_from_class` method.
        """

        # valid calls

        def helper_test(nr_calls=1):
            mock_rest = mock_connection_func("post")
            schema = Schema(mock_rest)
            schema._create_complex_properties_from_class(properties)
            self.assertEqual(mock_rest.post.call_count, nr_calls)
            properties_copy = deepcopy(properties["properties"])
            for prop in properties_copy:
                prop["dataType"] = [_capitalize_first_letter(dt) for dt in prop["dataType"]]
            mock_rest.post.assert_called_with(
                path="/schema/" + _capitalize_first_letter(properties["class"]) + "/properties",
                weaviate_object=properties_copy[0],
            )

        # no `properties` key
        mock_rest = mock_connection_func("post")
        schema = Schema(mock_rest)

        schema._create_complex_properties_from_class({})
        self.assertEqual(mock_rest.run_rest.call_count, 0)

        # no COMPLEX properties
        properties = {"properties": [{"dataType": ["text"]}]}
        schema._create_complex_properties_from_class(properties)
        self.assertEqual(mock_rest.post.call_count, 0)

        properties = {"properties": [{"dataType": ["text"]}, {"dataType": ["string"]}]}
        schema._create_complex_properties_from_class(properties)
        self.assertEqual(mock_rest.post.call_count, 0)

        # COMPLEX properties
        properties = {
            "class": "TestClass",
            "properties": [
                {"dataType": ["Test"], "description": "test description", "name": "test_prop"},
            ],
        }
        mock_rest = mock_connection_func("post")
        schema = Schema(mock_rest)
        schema._create_complex_properties_from_class(properties)
        self.assertEqual(mock_rest.post.call_count, 1)

        properties = {
            "class": "TestClass",
            "properties": [
                {"dataType": ["Test"], "description": "test description", "name": "test_prop"},
            ],
        }
        helper_test()

        properties["properties"][0]["indexInverted"] = True
        helper_test()

        properties["properties"][0]["moduleConfig"] = {"test": "ok!"}
        helper_test()

        properties["properties"].append(properties["properties"][0])  # add another property
        properties["properties"].append(properties["properties"][0])  # add another property
        helper_test(3)

        # with uncapitalized class_name
        properties["class"] = "testClass"
        helper_test(3)

        properties = {
            "class": "testClass",
            "properties": [
                {
                    "dataType": ["test", "myTest"],
                    "description": "test description",
                    "name": "test_prop",
                },
            ],
        }

        # invalid calls
        requests_error_message = "Property may not have been created properly."

        mock_rest = mock_connection_func("post", side_effect=RequestsConnectionError("TEST1"))
        schema = Schema(mock_rest)
        with self.assertRaises(RequestsConnectionError) as error:
            schema._create_complex_properties_from_class(properties)
        check_error_message(self, error, requests_error_message)

        mock_rest = mock_connection_func("post", status_code=404)
        schema = Schema(mock_rest)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            schema._create_complex_properties_from_class(properties)
        check_startswith_error_message(self, error, "Add properties to classes")

    def test__create_class_with_primitives(self):
        """
        Test the `_create_class_with_primitives` method.
        """

        # valid calls
        def helper_test(test_class, test_class_call):
            mock_rest = mock_connection_func("post")
            schema = Schema(mock_rest)
            schema._create_class_with_primitives(test_class)
            self.assertEqual(mock_rest.post.call_count, 1)
            mock_rest.post.assert_called_with(
                path="/schema",
                weaviate_object=test_class_call,
            )

        test_class = {
            "class": "TestClass",
            "properties": [
                {"dataType": ["int"], "name": "test_prop", "description": "None"},
                {"dataType": ["Test"], "name": "test_prop", "description": "None"},
            ],
        }
        test_class_call = {
            "class": "TestClass",
            "properties": [
                {"dataType": ["int"], "name": "test_prop", "description": "None"},
            ],
        }
        helper_test(test_class, test_class_call)

        test_class["description"] = "description"
        test_class_call["description"] = "description"
        helper_test(test_class, test_class_call)

        test_class["description"] = "description"
        test_class_call["description"] = "description"
        helper_test(test_class, test_class_call)

        test_class["vectorIndexType"] = "vectorIndexType"
        test_class_call["vectorIndexType"] = "vectorIndexType"
        helper_test(test_class, test_class_call)

        test_class["vectorIndexConfig"] = {"vectorIndexConfig": "vectorIndexConfig"}
        test_class_call["vectorIndexConfig"] = {"vectorIndexConfig": "vectorIndexConfig"}
        helper_test(test_class, test_class_call)

        test_class["vectorizer"] = "test_vectorizer"
        test_class_call["vectorizer"] = "test_vectorizer"
        helper_test(test_class, test_class_call)

        test_class["moduleConfig"] = {"moduleConfig": "moduleConfig"}
        test_class_call["moduleConfig"] = {"moduleConfig": "moduleConfig"}
        helper_test(test_class, test_class_call)

        test_class["shardingConfig"] = {"shardingConfig": "shardingConfig"}
        test_class_call["shardingConfig"] = {"shardingConfig": "shardingConfig"}
        helper_test(test_class, test_class_call)

        # multiple properties do not imply multiple `run_rest` calls
        test_class["properties"].append(test_class["properties"][0])  # add another property
        test_class["properties"].append(test_class["properties"][0])  # add another property
        test_class_call["properties"].append(test_class["properties"][0])  # add another property
        test_class_call["properties"].append(test_class["properties"][0])  # add another property
        helper_test(test_class, test_class_call)

        # with uncapitalized class_name
        test_class["class"] = "testClass"
        helper_test(test_class, test_class_call)

        # invalid calls
        requests_error_message = "Class may not have been created properly."

        mock_rest = mock_connection_func("post", side_effect=RequestsConnectionError("TEST1"))
        schema = Schema(mock_rest)
        with self.assertRaises(RequestsConnectionError) as error:
            schema._create_class_with_primitives(test_class)
        check_error_message(self, error, requests_error_message)

        mock_rest = mock_connection_func("post", status_code=404)
        schema = Schema(mock_rest)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            schema._create_class_with_primitives(test_class)
        check_startswith_error_message(self, error, "Create class")

    def test__create_classes_with_primitives(self):
        """
        Test the `_create_classes_with_primitives` method.
        """

        schema = Schema(Mock())

        mock_primitive = Mock()
        schema._create_class_with_primitives = mock_primitive

        schema._create_classes_with_primitives(list("Test!!"))
        self.assertEqual(mock_primitive.call_count, 6)

    def test__property_is_primitive(self):
        """
        Test the `_property_is_primitive` function.
        """

        from weaviate.schema.crud_schema import _property_is_primitive

        test_types_list = ["NOT Primitive", "Neither this one", "Nor This!"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["NOT Primitive", "boolean", "text"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["text"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["int"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["number"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["string"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["boolean"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["date"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["geoCoordinates"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["blob"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["phoneNumber"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["int[]", "number[]", "text[]", "string[]", "boolean[]", "date[]"]
        self.assertTrue(_property_is_primitive(test_types_list))
        test_types_list = ["int()"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["number()"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["text()"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["string()"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["boolean()"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = ["date()"]
        self.assertFalse(_property_is_primitive(test_types_list))
        test_types_list = [
            "string",
            "int",
            "boolean",
            "number",
            "date",
            "text",
            "geoCoordinates",
            "blob",
            "phoneNumber",
            "int[]",
            "number[]",
            "text[]",
            "string[]",
            "boolean[]",
            "date[]",
        ]
        self.assertTrue(_property_is_primitive(test_types_list))

    def test__get_primitive_properties(self):
        """
        Test the `_get_primitive_properties` function.
        """

        from weaviate.schema.crud_schema import _get_primitive_properties

        test_func = _get_primitive_properties

        properties_list = []
        self.assertEqual(test_func(properties_list), properties_list)

        properties_list = [{"dataType": ["text"]}]
        self.assertEqual(test_func(properties_list), properties_list)

        properties_list = [{"dataType": ["text"]}, {"dataType": ["int"]}]
        self.assertEqual(test_func(properties_list), properties_list)

        properties_list = [{"dataType": ["Test1"]}, {"dataType": ["Test2"]}]
        self.assertEqual(test_func(properties_list), [])

        properties_list = [
            {"dataType": ["text"]},
            {"dataType": ["int"]},
            {"dataType": ["Test1"]},
            {"dataType": ["Test2"]},
        ]
        self.assertEqual(
            test_func(properties_list), [{"dataType": ["text"]}, {"dataType": ["int"]}]
        )

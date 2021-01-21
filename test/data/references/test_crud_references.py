import unittest
from unittest.mock import Mock
import weaviate
from weaviate.connect import REST_METHOD_DELETE, REST_METHOD_POST, REST_METHOD_PUT
from test.util import replace_connection, add_run_rest_to_mock, run_rest_raise_connection_error


class TestReference(unittest.TestCase):

    def setUp(self):
        self.client = weaviate.Client("http://localhost:8080")
        self.uuid_1 = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        self.uuid_2 = "a36268d4-a6b5-5274-985f-45f13ce0c642"

    def test_delete(self):
        """
        Test `delete` method`.
        """
    
        # test exceptions
        with self.assertRaises(TypeError):
            self.client.data_object.reference.delete(1, "myProperty", self.uuid_2)
        with self.assertRaises(TypeError):
            self.client.data_object.reference.delete(self.uuid_1, "myProperty", 2)
        with self.assertRaises(TypeError):
            self.client.data_object.reference.delete(self.uuid_1, 3, self.uuid_2)
        with self.assertRaises(ValueError):
            self.client.data_object.reference.delete("str", "myProperty", self.uuid_2)
        with self.assertRaises(ValueError):
            self.client.data_object.reference.delete(self.uuid_1, "myProperty", "str")
        with self.assertRaises(TypeError):
            self.client.data_object.reference.delete(self.uuid_1, "myProperty", self.uuid_2, to_weaviate=4)
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=200)
            replace_connection(self.client, mock_obj)
            self.client.data_object.reference.delete(self.uuid_1, "myProperty", self.uuid_2)
        with self.assertRaises(weaviate.RequestsConnectionError):
            mock_obj = Mock()
            mock_obj.run_rest.side_effect = run_rest_raise_connection_error
            replace_connection(self.client, mock_obj)
            self.client.data_object.reference.delete(self.uuid_1, "myProperty", self.uuid_2)

        # test valid calls
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=204)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.reference.delete(
            self.uuid_1,
            "myProperty",
            self.uuid_2
        )
        self.assertIsNone(response)

        response = self.client.data_object.reference.delete(
            self.uuid_1,
            "hasItem",
            f"http://localhost:8080/v1/objects/{self.uuid_2}"
        )
        self.assertIsNone(response)
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list

        call_kwargs = call_args_list[0][1]
        self.assertEqual(f"/objects/{self.uuid_1}/references/myProperty", call_kwargs["path"])
        self.assertEqual(REST_METHOD_DELETE, call_kwargs["rest_method"])
        self.assertEqual({"beacon": f"weaviate://localhost/{self.uuid_2}"}, call_kwargs["weaviate_object"])

        call_kwargs = call_args_list[1][1]
        self.assertEqual(f"/objects/{self.uuid_1}/references/hasItem", call_kwargs["path"])
        self.assertEqual(REST_METHOD_DELETE, call_kwargs["rest_method"])
        self.assertEqual({"beacon": f"weaviate://localhost/{self.uuid_2}"}, call_kwargs["weaviate_object"])

    def test_add(self):
        """
        Test the `add` method.
        """
        
        # test exceptions
        with self.assertRaises(TypeError):
            self.client.data_object.reference.add(1, "prop", self.uuid_1)
        with self.assertRaises(TypeError):
            self.client.data_object.reference.add(self.uuid_1, 1, self.uuid_2)
        with self.assertRaises(TypeError):
            self.client.data_object.reference.add(self.uuid_1, "prop", 1)
        with self.assertRaises(ValueError):
            self.client.data_object.reference.add("my UUID", "prop", self.uuid_2)
        with self.assertRaises(ValueError):
            self.client.data_object.reference.add(self.uuid_1, "prop", "my uuid")
        with self.assertRaises(ValueError):
            self.client.data_object.reference.add(f"http://localhost:8080/v1/objects/{self.uuid_1}", "prop",
                                        "http://localhost:8080/v1/objects/MY_UUID")
        with self.assertRaises(ValueError):
            self.client.data_object.reference.add("http://localhost:8080/v1/objects/My-UUID", "prop",
                                        f"http://localhost:8080/v1/objects/{self.uuid_2}")
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204)
            replace_connection(self.client, mock_obj)
            self.client.data_object.reference.add(self.uuid_1, "myProperty", self.uuid_2)
        with self.assertRaises(weaviate.RequestsConnectionError):
            mock_obj = Mock()
            mock_obj.run_rest.side_effect = run_rest_raise_connection_error
            replace_connection(self.client, mock_obj)
            self.client.data_object.reference.add(self.uuid_1, "myProperty", self.uuid_2)

        # test valid calls
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(self.client, connection_mock)

        # 1. Plain
        response = self.client.data_object.reference.add(
            "3250b0b8-eaf7-499b-ac68-9084c9c82d0f",
            "hasItem",
            "99725f35-f12a-4f36-a2e2-0d41501f4e0e"
        )
        self.assertIsNone(response)

        # 2. using url
        response = self.client.data_object.reference.add(
            "http://localhost:8080/v1/objects/7591be77-5959-4386-9828-423fc5096e87",
            "hasItem",
            "http://localhost:8080/v1/objects/1cd80c11-29f0-453f-823c-21547b1511f0"
        )
        self.assertIsNone(response)

        # 3. using weavaite url
        response = self.client.data_object.reference.add(
            "weaviate://localhost/f8def983-87e7-4e21-bf10-e32e2de3efcf",
            "hasItem",
            "weaviate://localhost/e40aaef5-d3e5-44f1-8ec4-3eafc8475078"
        )
        self.assertIsNone(response)

        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list

        # 1.
        call_kwargs = call_args_list[0][1]
        self.assertEqual("/objects/3250b0b8-eaf7-499b-ac68-9084c9c82d0f/references/hasItem", call_kwargs["path"])
        self.assertEqual(REST_METHOD_POST, call_kwargs["rest_method"])
        self.assertEqual({'beacon': 'weaviate://localhost/99725f35-f12a-4f36-a2e2-0d41501f4e0e'}, call_kwargs["weaviate_object"])

        # 2.
        call_kwargs = call_args_list[1][1]
        self.assertEqual("/objects/7591be77-5959-4386-9828-423fc5096e87/references/hasItem", call_kwargs["path"])
        self.assertEqual(REST_METHOD_POST, call_kwargs["rest_method"])
        self.assertEqual({'beacon': 'weaviate://localhost/1cd80c11-29f0-453f-823c-21547b1511f0'}, call_kwargs["weaviate_object"])

        # 3.
        call_kwargs = call_args_list[2][1]
        self.assertEqual("/objects/f8def983-87e7-4e21-bf10-e32e2de3efcf/references/hasItem", call_kwargs["path"])
        self.assertEqual(REST_METHOD_POST, call_kwargs["rest_method"])
        self.assertEqual({'beacon': 'weaviate://localhost/e40aaef5-d3e5-44f1-8ec4-3eafc8475078'}, call_kwargs["weaviate_object"])

    def test_update(self):
        """
        Test the `update` method.
        """

        # test exceptions
        with self.assertRaises(TypeError):
            self.client.data_object.reference.update(1, "prop", [self.uuid_1])
        with self.assertRaises(TypeError):
            self.client.data_object.reference.update(self.uuid_1, 1, [self.uuid_2])
        with self.assertRaises(TypeError):
            self.client.data_object.reference.update(self.uuid_1, "prop", 1)
        with self.assertRaises(TypeError):
            self.client.data_object.reference.update(self.uuid_1, "prop", [1])
        with self.assertRaises(ValueError):
            self.client.data_object.reference.update("my UUID", "prop", self.uuid_2)
        with self.assertRaises(ValueError):
            self.client.data_object.reference.update(self.uuid_1, "prop", "my uuid")
        with self.assertRaises(ValueError):
            self.client.data_object.reference.update(self.uuid_1, "prop", ["my uuid"])
        with self.assertRaises(ValueError):
            self.client.data_object.reference.update(f"http://localhost:8080/v1/objects/{self.uuid_1}", "prop",
                                        "http://localhost:8080/v1/objects/MY_UUID")
        with self.assertRaises(ValueError):
            self.client.data_object.reference.update("http://localhost:8080/v1/objects/My-UUID", "prop",
                                        f"http://localhost:8080/v1/objects/{self.uuid_2}")
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204)
            replace_connection(self.client, mock_obj)
            self.client.data_object.reference.update(self.uuid_1, "myProperty", self.uuid_2)
        with self.assertRaises(weaviate.RequestsConnectionError):
            mock_obj = Mock()
            mock_obj.run_rest.side_effect = run_rest_raise_connection_error
            replace_connection(self.client, mock_obj)
            self.client.data_object.reference.update(self.uuid_1, "myProperty", self.uuid_2)

        # test valid calls
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.reference.update(
            "de998e81-fa66-440e-a1de-2a2013667e77",
            "hasAwards",
            "fc041624-4ddf-4b76-8e09-a5b0b9f9f832"
        )
        self.assertIsNone(response)

        response = self.client.data_object.reference.update(
            "4e44db9b-7f9c-4cf4-a3a0-b57024eefed0",
            "hasAwards",
            [
                "17ee17bd-a09a-49ff-adeb-d242f25f390d",
                "f8c25386-707c-40c0-b7b9-26cc0e9b2bd1",
                "d671dc52-dce4-46e7-8731-b722f19420c8"
            ]
        )
        self.assertIsNone(response)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]

        self.assertEqual("/objects/de998e81-fa66-440e-a1de-2a2013667e77/references/hasAwards", call_kwargs["path"])
        self.assertEqual(REST_METHOD_PUT, call_kwargs["rest_method"])
        self.assertEqual([{'beacon': 'weaviate://localhost/fc041624-4ddf-4b76-8e09-a5b0b9f9f832'}], call_kwargs["weaviate_object"])

        call_kwargs = call_args_list[1][1]

        self.assertEqual("/objects/4e44db9b-7f9c-4cf4-a3a0-b57024eefed0/references/hasAwards", call_kwargs["path"])
        self.assertEqual(REST_METHOD_PUT, call_kwargs["rest_method"])
        self.assertEqual([{'beacon': 'weaviate://localhost/17ee17bd-a09a-49ff-adeb-d242f25f390d'},
                          {'beacon': 'weaviate://localhost/f8c25386-707c-40c0-b7b9-26cc0e9b2bd1'},
                          {'beacon': 'weaviate://localhost/d671dc52-dce4-46e7-8731-b722f19420c8'}], call_kwargs["weaviate_object"])       

    def test__try_run_rest(self):
        """
        Test `_try_run_rest` method, only for the method exception.
        """

        with self.assertRaises(ValueError):
            self.client.data_object.reference._try_run_rest("", "", "", "validate")
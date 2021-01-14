import unittest
from unittest.mock import patch
import weaviate
from weaviate.connect import REST_METHOD_POST, REST_METHOD_PUT, REST_METHOD_PATCH, REST_METHOD_DELETE, REST_METHOD_GET
from test.testing_util import run_rest_raise_connection_error, Mock
from test.testing_util import add_run_rest_to_mock, replace_connection


class TestDataObject(unittest.TestCase):

    def setUp(self):

        self.client = weaviate.Client("http://localhost:8080")

    def test_create(self):
        """
        Test the `create` method.
        """

        # test exceptions
        with self.assertRaises(TypeError):
            self.client.data_object.create(None, "Class")
        with self.assertRaises(TypeError):
            self.client.data_object.create(224345, "Class")
        with self.assertRaises(TypeError):
            self.client.data_object.create({'name': 'Optimus Prime'}, None)
        with self.assertRaises(TypeError):
            self.client.data_object.create({'name': 'Optimus Prime'}, "Transformer", 19210)
        with self.assertRaises(ValueError):
            self.client.data_object.create({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")
        with self.assertRaises(TypeError):
            self.client.data_object.create({'name': 'Optimus Prime'}, "Transformer", None, 1234)

        with self.assertRaises(weaviate.RequestsConnectionError):
            connection_mock = Mock()  # Mock calling weaviate
            connection_mock.run_rest.side_effect = run_rest_raise_connection_error
            self.client._connection = connection_mock
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")

        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204, return_json={})
            replace_connection(self.client, mock_obj)
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")

        with self.assertRaises(weaviate.ObjectAlreadyExistsException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204, return_json={"error" : [{"message" : "already exists"}]})
            replace_connection(self.client, mock_obj)
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        
        with self.assertRaises(TypeError):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204, return_json=[])
            replace_connection(self.client, mock_obj)
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")

        # test valid calls
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, {"id": 0}, status_code=200)
        replace_connection(self.client, connection_mock)


        object_ = {"lyrics": "da da dadadada dada, da da dadadada da, da da dadadada da, da da dadadada da Tequila"}
        class_name = "KaraokeSongs"
        vector_weights = {
            "da": "1",
            "dadadada": "client + 0.5",
            "tequila": "*15"
        }

        rest_object = {
            "class": "KaraokeSongs",
            "properties": object_,
            "vectorWeights": vector_weights
        }

        uuid = self.client.data_object.create(object_, class_name, None, vector_weights)
        self.assertEqual(uuid, str(0))
        connection_mock.run_rest.assert_called_with("/objects", REST_METHOD_POST, rest_object)

    def test_update(self):
        """
        Test the `update` method.
        """

        # test exceptions
        
        with self.assertRaises(weaviate.RequestsConnectionError):
            connection_mock = Mock()  # Mock calling weaviate
            connection_mock.run_rest.side_effect = run_rest_raise_connection_error
            self.client._connection = connection_mock
            self.client.data_object.update(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d"
            )

        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204, return_json={})
            replace_connection(self.client, mock_obj)
            self.client.data_object.update(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d"
            )

        # test valid calls
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.update({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertIsNone(response)

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2}
        }
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with(
            "/objects/27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            REST_METHOD_PUT, weaviate_obj)

    def test_merge(self):
        """
        Test the `merge` method.
        """

        with self.assertRaises(TypeError):
            self.client.data_object.merge(None, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
        with self.assertRaises(TypeError):
            self.client.data_object.merge({"A": "B"}, 35, "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
        with self.assertRaises(TypeError):
            self.client.data_object.merge(({"A": "B"}, "Class", 1238234))
        with self.assertRaises(ValueError):
            self.client.data_object.merge({"A": "B"}, "Class", "NOT-A-valid-uuid")
        with self.assertRaises(weaviate.RequestsConnectionError):
            self.client.data_object.merge(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d"
            )

        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=200, return_json={})
            replace_connection(self.client, mock_obj)
            self.client.data_object.merge(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d"
            )

        # test valid calls
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, status_code=204)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.merge({"A": "B"}, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
        self.assertIsNone(response)

        weaviate_obj = {
            "id": "ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            "class": "Class",
            "properties": {"A": "B"}
        }
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with(
            "/objects/ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            REST_METHOD_PATCH, weaviate_obj)

    def test_delete(self):
        """
        Test the `delete` method.
        """

        with self.assertRaises(TypeError):
            self.client.data_object.delete(4)
        with self.assertRaises(ValueError):
            self.client.data_object.delete("Hallo Wereld")
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            connection_mock = Mock()
            add_run_rest_to_mock(connection_mock, status_code=404)
            replace_connection(self.client, connection_mock)
            self.client.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")


        # 1. Succesfully delete something
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, status_code=204)
        replace_connection(self.client, connection_mock)

        object_id = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        self.client.data_object.delete(object_id)
        connection_mock.run_rest.assert_called_with("/objects/" + object_id, REST_METHOD_DELETE)

    def test_get_by_id(self):
        """
        Test the `get_by_id` method.
        """

        # test exceptions
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_func = Mock()
            mock_obj = Mock()
            mock_obj.configure_mock(status_code=300)
            mock_func.return_value = mock_obj
            self.client.data_object._get_object_response = mock_func
            self.client.data_object.get_by_id("some_id")

        # test valit calls
        # status_code 200
        mock_func = Mock()
        mock_obj = Mock()
        mock_obj.configure_mock(status_code=200)
        mock_obj.json.return_value = "all good!"
        mock_func.return_value = mock_obj
        self.client.data_object._get_object_response = mock_func
        result = self.client.data_object.get_by_id("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(result, "all good!")
        # status_code 200
        mock_func = Mock()
        mock_obj = Mock()
        mock_obj.configure_mock(status_code=404)
        mock_obj.json.return_value = "all good!"
        mock_func.return_value = mock_obj
        self.client.data_object._get_object_response = mock_func
        result = self.client.data_object.get_by_id("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertIsNone(result)

    def test__get_object_response(self):
        """
        Test the `_get_object_response` method.
        """

        with self.assertRaises(TypeError):
            self.client.data_object._get_object_response("UUID", {}, False)
        with self.assertRaises(weaviate.RequestsConnectionError):
            connection_mock = Mock()  # Mock calling weaviate
            connection_mock.run_rest.side_effect = run_rest_raise_connection_error
            self.client._connection = connection_mock
            self.client.data_object._get_object_response("UUID", [], False)

        return_value = {
            "additional": {
                "interpretation": {
                    "source": [
                        {
                            "concept": "person",
                            "occurrence": 6627994,
                            "weight": 0.10000000149011612
                        }, {
                            "concept": "alan",
                            "occurrence": 398345,
                            "weight": 0.4580279588699341
                        }, {
                            "concept": "turing",
                            "occurrence": 31261,
                            "weight": 0.7820844054222107
                        }
                    ]
                }
            },
            "vector": [0.095590845, 0.24995095, -0.19630778],
            "class": "Person",
            "creationTimeUnix": 1599550471320,
            "id": "1c9cd584-88fe-5010-83d0-017cb3fcb446",
            "lastUpdateTimeUnix": 1599550471320,
            "meta": {
                "vector": [0.095590845, 0.24995095, 0.11117377]
            },
            "properties": {
                "name": "Alan Turing"
            },
            "vectorWeights": None
        }

        # test valid calls
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, return_value)
        replace_connection(self.client, connection_mock)

        result = self.client.data_object._get_object_response("21fa7bc8-011f-4066-861e-f62c285f09c8",
                                         additional_properties=["interpretation", "empty"], with_vector=True)

        self.assertEqual(return_value, result.json())
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/objects/21fa7bc8-011f-4066-861e-f62c285f09c8", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])
        self.assertEqual({"include": "interpretation,empty,vector"}, call_kwargs["params"])

        # without vector
        result = self.client.data_object._get_object_response("21fa7bc8-011f-4066-861e-f62c285f09c8",
                                         additional_properties=["interpretation", "empty"], with_vector=False)

        self.assertEqual(return_value, result.json())
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/objects/21fa7bc8-011f-4066-861e-f62c285f09c8", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])
        self.assertEqual({"include": "interpretation,empty"}, call_kwargs["params"])

    def test_get(self):
        """
        Test the `get` method.
        """

        # test exceptions
        with self.assertRaises(weaviate.RequestsConnectionError):
            connection_mock = Mock()  # Mock calling weaviate
            connection_mock.run_rest.side_effect = run_rest_raise_connection_error
            mock_func = Mock()
            mock_func.return_value = {"include" : "param1,param2"} 
            self.client.data_object._get_params = mock_func
            replace_connection(self.client, connection_mock)
            self.client.data_object.get()
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            connection_mock = Mock()  # Mock calling weaviate
            add_run_rest_to_mock(connection_mock, status_code=204)
            mock_func = Mock()
            mock_func.return_value = {"include" : "param1,param2"} 
            self.client.data_object._get_params = mock_func
            replace_connection(self.client, connection_mock)
            self.client.data_object.get()

        # test valid calls
        connection_mock = Mock()  # Mock calling weaviate
        return_value_get = {"my_key": 12341}
        add_run_rest_to_mock(connection_mock, return_value_get, status_code=200)
        replace_connection(self.client, connection_mock)

        result = self.client.data_object.get()
        self.assertEqual(return_value_get, result)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/objects", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])

        self.setUp()
        return_value_get = {"my_key": 12345}

        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, {"my_key": 12345})
        replace_connection(self.client, connection_mock)

        result = self.client.data_object.get(["nearestNeighbors"], True)
        self.assertEqual(return_value_get, result)

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/objects", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])
        self.assertEqual({"include": "nearestNeighbors,vector"}, call_kwargs["params"])

    def test_exists(self):
        """
        Test the `exists` method.
        """

        # test exceptions
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_func = Mock()
            mock_obj = Mock()
            mock_obj.configure_mock(status_code=300)
            mock_func.return_value = mock_obj
            self.client.data_object._get_object_response = mock_func
            self.client.data_object.exists("some_id")

        # test valit calls
        # status_code 200
        mock_func = Mock()
        mock_obj = Mock()
        mock_obj.configure_mock(status_code=200)
        mock_obj.json.return_value = "all good!"
        mock_func.return_value = mock_obj
        self.client.data_object._get_object_response = mock_func
        result = self.client.data_object.exists("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(result, True)
        # status_code 200
        mock_func = Mock()
        mock_obj = Mock()
        mock_obj.configure_mock(status_code=404)
        mock_obj.json.return_value = "all good!"
        mock_func.return_value = mock_obj
        self.client.data_object._get_object_response = mock_func
        result = self.client.data_object.exists("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(result, False)

    def test_validate(self):
        """
        Test the `validate` method.
        """

        # test exceptions
        with self.assertRaises(TypeError):
            self.client.data_object.validate({}, "Name", 1)
        with self.assertRaises(TypeError):
            self.client.data_object.validate({}, ["Name"], "73802305-c0da-427e-b21c-d6779a22f35f")

        with self.assertRaises(weaviate.RequestsConnectionError):
            mock_obj = Mock() # Mock calling weaviate
            mock_obj.run_rest.side_effect = run_rest_raise_connection_error
            replace_connection(self.client, mock_obj)
            self.client.data_object.validate({"name": "Alan Greenspan"}, "CoolestPersonEver", "73802305-c0da-427e-b21c-d6779a22f35f")

        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock() # Mock calling weaviate
            mock_obj = add_run_rest_to_mock(mock_obj, status_code=204, return_json={})
            replace_connection(self.client, mock_obj)
            self.client.data_object.validate({"name": "Alan Greenspan"}, "CoolestPersonEver", "73802305-c0da-427e-b21c-d6779a22f35f")

        # test valid calls
        # test for status_code 200
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=200)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {'error': None, 'valid': True})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2}
        }
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with(
            "/objects/validate",
            REST_METHOD_POST, weaviate_obj)

        # test for status_code 422
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=422, return_json={"error": "Not OK!"})
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {'error': "Not OK!", 'valid': False})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2}
        }
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with(
            "/objects/validate",
            REST_METHOD_POST, weaviate_obj)
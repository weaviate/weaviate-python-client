import unittest
from unittest.mock import patch, Mock
import weaviate
from weaviate.connect import REST_METHOD_POST, REST_METHOD_PUT, REST_METHOD_PATCH, REST_METHOD_DELETE, REST_METHOD_GET
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException, ObjectAlreadyExistsException
from test.util import mock_run_rest, replace_connection


class TestDataObject(unittest.TestCase):

    def setUp(self):

        self.client = weaviate.Client("http://localhost:8080")

    @patch('weaviate.data.crud_data._get_dict_from_object', side_effect=lambda x:x)
    @patch('weaviate.data.crud_data.get_vector', side_effect=lambda x:x)
    def test_create(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `create` method.
        """

        # invalid calls
        class_name_error_message = lambda dt: f"Expected class_name of type str but was: {dt}"
        uuid_type_error_message = lambda dt: f"Expected uuid to be of type str but was: {dt}"
        uuid_value_error_message = "Given uuid does not have a valid form"
        requests_error_message = 'Test! Connection error, object was not added to weaviate.'
        unexpected_error_message = 'Test! Unexpected exception please report this excetpion in an issue.'

        # tests
        with self.assertRaises(TypeError) as error:
            self.client.data_object.create({'name': 'Optimus Prime'}, ["Transformer"])
        self.assertEqual(str(error.exception), class_name_error_message(list))
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()
        

        with self.assertRaises(TypeError) as error:
            self.client.data_object.create({'name': 'Optimus Prime'}, "Transformer", 19210)
        self.assertEqual(str(error.exception), uuid_type_error_message(int))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        

        with self.assertRaises(ValueError) as error:
            self.client.data_object.create({'name': 'Optimus Prime'}, "Transformer", "1234_1234_1234_1234")
        self.assertEqual(str(error.exception), uuid_value_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()


        mock_obj = mock_run_rest(side_effect=RequestsConnectionError("Test!"))
        replace_connection(self.client, mock_obj)
        with self.assertRaises(weaviate.RequestsConnectionError) as error:
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        self.assertEqual(str(error.exception), requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        

        mock_obj = mock_run_rest(status_code=204, return_json={})
        replace_connection(self.client, mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        self.assertTrue(str(error.exception).startswith("Creating object"))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        mock_obj = mock_run_rest(status_code=204, return_json={"error" : [{"message" : "already exists"}]})
        replace_connection(self.client, mock_obj)
        with self.assertRaises(ObjectAlreadyExistsException) as error:
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        self.assertEqual(str(error.exception), "None")
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        
        mock_obj = mock_run_rest(status_code=204, return_json={})
        replace_connection(self.client, mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        self.assertTrue(str(error.exception).startswith("Creating object"))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        mock_obj = mock_run_rest()
        mock_json = Mock(status_code=204)
        mock_json.json.side_effect = Exception("Test!")
        mock_obj.run_rest.return_value = mock_json
        replace_connection(self.client, mock_obj)
        with self.assertRaises(Exception) as error:
            self.client.data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        self.assertEqual(str(error.exception), unexpected_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # # test valid calls
        ## without vector argument
        connection_mock = mock_run_rest(return_json={"id": 0}, status_code=200)
        replace_connection(self.client, connection_mock)

        object_ = {"lyrics": "da da dadadada dada, da da dadadada da, da da dadadada da, da da dadadada da Tequila"}
        class_name = "KaraokeSongs"
        vector = [1., 2.]
        id_ = "ae6d51d6-b4ea-5a03-a808-6aae990bdebf"

        rest_object = {
            "class": class_name,
            "properties": object_,
            "id": id_
        }

        uuid = self.client.data_object.create(object_, class_name, id_)
        self.assertEqual(uuid, "0")
        connection_mock.run_rest.assert_called_with("/objects", REST_METHOD_POST, rest_object)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        ## with vector argument
        connection_mock = mock_run_rest(return_json={"id": 0}, status_code=200)
        replace_connection(self.client, connection_mock)

        object_ = {"lyrics": "da da dadadada dada, da da dadadada da, da da dadadada da, da da dadadada da Tequila"}
        class_name = "KaraokeSongs"
        vector = [1., 2.]
        id_ = "ae6d51d6-b4ea-5a03-a808-6aae990bdebf"

        rest_object = {
            "class": class_name,
            "properties": object_,
            "vector": vector,
            "id": id_
        }

        uuid = self.client.data_object.create(object_, class_name, id_, vector)
        self.assertEqual(uuid, "0")
        connection_mock.run_rest.assert_called_with("/objects", REST_METHOD_POST, rest_object)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()

    @patch('weaviate.data.crud_data._get_dict_from_object', side_effect=lambda x:x)
    @patch('weaviate.data.crud_data.get_vector', side_effect=lambda x:x)
    def test_update(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `update` method.
        """

        # error messages
        class_type_error_message = "Class must be type str"
        uuid_type_error_message = "UUID must be type str"
        uuid_value_error_message = "Not a proper UUID"
        requests_error_message = 'Test! Connection error, object was not updated(REST PATCH).'
        unexpected_error_message = "Update of the object not successful"
        
        with self.assertRaises(TypeError) as error:
            self.client.data_object.update({"A": "B"}, 35, "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
        self.assertEqual(str(error.exception), class_type_error_message)
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(TypeError) as error:
            self.client.data_object.update({"A": "B"}, "Class", 1238234)
        self.assertEqual(str(error.exception), uuid_type_error_message)
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(ValueError) as error:
            self.client.data_object.update({"A": "B"}, "Class", "NOT-A-valid-uuid")
        self.assertEqual(str(error.exception), uuid_value_error_message)
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        mock_obj = mock_run_rest(side_effect=RequestsConnectionError("Test!"))
        replace_connection(self.client, mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.data_object.update(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(str(error.exception), requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(UnexpectedStatusCodeException) as error:
            mock_obj = mock_run_rest(status_code=200, return_json={})
            replace_connection(self.client, mock_obj)
            self.client.data_object.update(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test valid calls
        ## without vector argument
        connection_mock = mock_run_rest(status_code=204)
        replace_connection(self.client, connection_mock)
        self.client.data_object.update({"A": "B"}, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
        weaviate_obj = {
            "id": "ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            "class": "Class",
            "properties": {"A": "B"}
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            REST_METHOD_PATCH, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        ## with vector argument
        connection_mock = mock_run_rest(status_code=204)
        replace_connection(self.client, connection_mock)
        self.client.data_object.update({"A": "B"}, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf", vector=[2., 4.])
        weaviate_obj = {
            "id": "ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            "class": "Class",
            "properties": {"A": "B"},
            "vector": [2., 4.]
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            REST_METHOD_PATCH, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()
    
    @patch('weaviate.data.crud_data._get_dict_from_object', side_effect=lambda x:x)
    @patch('weaviate.data.crud_data.get_vector', side_effect=lambda x:x)
    def test_replace(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `replace` method.
        """

        # error messages
        requests_error_message = 'Test! Connection error, object was not replaced(REST PUT).'
        unexpected_error_message = "Replace object"

        # test exceptions
        mock_obj = mock_run_rest(side_effect=RequestsConnectionError("Test!"))
        replace_connection(self.client, mock_obj)
        with self.assertRaises(weaviate.RequestsConnectionError) as error:
            self.client.data_object.replace(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(str(error.exception), requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        mock_obj = mock_run_rest(status_code=204, return_json={})
        replace_connection(self.client, mock_obj)
        with self.assertRaises(weaviate.UnexpectedStatusCodeException) as error:
            self.client.data_object.replace(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test valid calls
        ## without vector argument
        connection_mock = mock_run_rest()
        replace_connection(self.client, connection_mock)
        self.client.data_object.replace({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2}
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            REST_METHOD_PUT, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # with vector argument
        connection_mock = mock_run_rest()
        replace_connection(self.client, connection_mock)
        self.client.data_object.replace({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d", vector=[3.,5, 7])
        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
            "vector": [3.,5, 7]
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            REST_METHOD_PUT, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()

    def test_delete(self):
        """
        Test the `delete` method.
        """

        # error messages
        uuid_type_error_message = "UUID must be type str"
        uuid_value_error_message = "UUID does not have proper form"
        requests_error_message = 'Test! Connection error, object could not be deleted.'
        unexpected_error_message = "Delete object"

        with self.assertRaises(TypeError) as error:
            self.client.data_object.delete(4)
        self.assertEqual(str(error.exception), uuid_type_error_message)

        with self.assertRaises(ValueError) as error:
            self.client.data_object.delete("Hallo Wereld")
        self.assertEqual(str(error.exception), uuid_value_error_message)

        connection_mock = mock_run_rest(side_effect=RequestsConnectionError('Test!'))
        replace_connection(self.client, connection_mock)
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
        self.assertEqual(str(error.exception), requests_error_message)

        connection_mock = mock_run_rest(status_code=404)
        replace_connection(self.client, connection_mock)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))

        # 1. Succesfully delete something
        connection_mock = mock_run_rest(status_code=204)
        replace_connection(self.client, connection_mock)

        object_id = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        self.client.data_object.delete(object_id)
        connection_mock.run_rest.assert_called_with("/objects/" + object_id, REST_METHOD_DELETE)

    def test_get_by_id(self):
        """
        Test the `get_by_id` method.
        """

        mock_get = Mock(return_value = "Test")
        self.client.data_object.get = mock_get
        self.client.data_object.get_by_id(
            uuid="UUID",
            additional_properties=["Test", "list"],
            with_vector=True
        )
        mock_get.assert_called_with(
            uuid="UUID",
            additional_properties=["Test", "list"],
            with_vector=True
        )

        self.client.data_object.get_by_id(
            uuid="UUID2",
            additional_properties=["Test"],
            with_vector=False
        )
        mock_get.assert_called_with(
            uuid="UUID2",
            additional_properties=["Test"],
            with_vector=False
        )
    @patch('weaviate.data.crud_data._get_params')
    def test_get(self, mock_get_params):
        """
        Test the `get` method.
        """

        # error messages
        requests_error_message = 'Test! Connection error when getting object/s'
        unexpected_error_message = "Get object/s"

        # test exceptions
        replace_connection(self.client, mock_run_rest(side_effect=RequestsConnectionError("Test!")))
        with self.assertRaises(weaviate.RequestsConnectionError) as error:
            self.client.data_object.get()
        self.assertEqual(str(error.exception), requests_error_message)
        
        replace_connection(self.client, mock_run_rest(status_code=204))
        with self.assertRaises(weaviate.UnexpectedStatusCodeException) as error:
            self.client.data_object.get()
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))

        # test valid calls
        return_value_get = {"my_key": 12341}
        mock_get_params.return_value = {'include': "test1,test2"}
        connection_mock = mock_run_rest(return_json=return_value_get, status_code=200)
        replace_connection(self.client, connection_mock)
        result = self.client.data_object.get()
        self.assertEqual(result, return_value_get)
        connection_mock.run_rest.assert_called_with("/objects", REST_METHOD_GET, params={'include': "test1,test2"})

        return_value_get = {"my_key": '12341'}
        mock_get_params.return_value = {'include': "test1,test2"}
        connection_mock = mock_run_rest(return_json=return_value_get, status_code=200)
        replace_connection(self.client, connection_mock)
        result = self.client.data_object.get(uuid="TestUUID")
        self.assertEqual(result, return_value_get)
        connection_mock.run_rest.assert_called_with("/objects/TestUUID", REST_METHOD_GET, params={'include': "test1,test2"})

        return_value_get = {"my_key": '12341'}
        mock_get_params.return_value = {'include': "test1,test2"}
        connection_mock = mock_run_rest(return_json=return_value_get, status_code=404)
        replace_connection(self.client, connection_mock)
        result = self.client.data_object.get(uuid="TestUUID")
        self.assertIsNone(result)
        connection_mock.run_rest.assert_called_with("/objects/TestUUID", REST_METHOD_GET, params={'include': "test1,test2"})

    @patch('weaviate.data.crud_data.DataObject.get')
    def test_exists(self, mock_get):
        """
        Test the `exists` method.
        """

        # error messages
        unexpected_error_message = "Object exists"
        # test exceptions
        mock_obj = Mock(status_code=300)
        mock_get.return_value = mock_obj
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.data_object.exists("some_id")
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))
        mock_get.assert_called()

        # test valit calls
        ## status_code 200
        mock_obj = Mock(status_code=200)
        mock_get.return_value = mock_obj
        result = self.client.data_object.exists("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(result, True)

        ## status_code 200
        mock_obj = Mock(status_code=404)
        mock_get.return_value = mock_obj
        result = self.client.data_object.exists("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(result, False)

    @patch('weaviate.data.crud_data._get_dict_from_object', side_effect=lambda x:x)
    @patch('weaviate.data.crud_data.get_vector', side_effect=lambda x:x)
    def test_validate(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `validate` method.
        """

        # error messages
        uuid_type_error_message = "UUID must be of type `str`"
        class_name_error_message = lambda dt: f"Expected class_name of type `str` but was: {dt}"
        requests_error_message = 'Test! Connection error, object was not validated against weaviate.'
        unexpected_error_message = "Validate object"

        # test exceptions
        with self.assertRaises(TypeError) as error:
            self.client.data_object.validate({}, "Name", 1)
        self.assertEqual(str(error.exception), uuid_type_error_message)
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(TypeError) as error:
            self.client.data_object.validate({}, ["Name"], "73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(str(error.exception), class_name_error_message(list))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        replace_connection(self.client, mock_run_rest(side_effect=RequestsConnectionError("Test!")))
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.data_object.validate({"name": "Alan Greenspan"}, "CoolestPersonEver", "73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertEqual(str(error.exception), requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        replace_connection(self.client, mock_run_rest(status_code=204, return_json={}))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.data_object.validate({"name": "Alan Greenspan"}, "CoolestPersonEver", "73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test valid calls
        # test for status_code 200 without vector argument
        connection_mock = mock_run_rest(status_code=200)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {'error': None, 'valid': True})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2}
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/validate",
            REST_METHOD_POST, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test for status_code 422
        connection_mock = mock_run_rest(status_code=422, return_json={"error": "Not OK!"})
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {'error': "Not OK!", 'valid': False})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2}
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/validate",
            REST_METHOD_POST, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test for status_code 200 with vector argument
        connection_mock = mock_run_rest(status_code=200)
        replace_connection(self.client, connection_mock)

        response = self.client.data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d", vector=[-9.8, 6.66])
        self.assertEqual(response, {'error': None, 'valid': True})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
            "vector": [-9.8, 6.66]
        }
        connection_mock.run_rest.assert_called_with(
            "/objects/validate",
            REST_METHOD_POST, weaviate_obj)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()

    def test__get_params(self):
        """
        Test the `_get_params` function.
        """
        
        from weaviate.data.crud_data import _get_params

        # error messages
        type_error_message = lambda dt: f"Additional properties must be of type list but are {dt}"

        with self.assertRaises(TypeError) as error:
            _get_params("Test", False)
        self.assertEqual(str(error.exception), type_error_message(str))

        self.assertEqual(_get_params(["test1","test2"], False), {'include': "test1,test2"})
        self.assertEqual(_get_params(None, True), {'include': "vector"})
        self.assertEqual(_get_params([], True), {'include': "vector"})
        self.assertEqual(_get_params(["test1","test2"], True), {'include': "test1,test2,vector"})

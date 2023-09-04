import unittest
from unittest.mock import patch, Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.data import DataObject
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    ObjectAlreadyExistsException,
)


class TestDataObject(unittest.TestCase):
    @patch("weaviate.data.crud_data._get_dict_from_object", side_effect=lambda x: x)
    @patch("weaviate.data.crud_data.get_valid_uuid", side_effect=lambda x: x)
    @patch("weaviate.data.crud_data.get_vector", side_effect=lambda x: x)
    def test_create(self, mock_get_vector, mock_get_valid_uuid, mock_get_dict_from_object):
        """
        Test the `create` method.
        """

        def reset():
            """
            Reset patched objects
            """

            mock_get_valid_uuid.reset_mock()  # reset called
            mock_get_vector.reset_mock()  # reset called
            mock_get_dict_from_object.reset_mock()  # reset_called

        data_object = DataObject(Mock())

        # invalid calls
        class_name_error_message = lambda dt: f"Expected class_name of type str but was: {dt}"
        requests_error_message = "Object was not added to Weaviate."

        # tests
        with self.assertRaises(TypeError) as error:
            data_object.create({"name": "Optimus Prime"}, ["Transformer"])
        check_error_message(self, error, class_name_error_message(list))
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_not_called()

        # test invalid consistency level
        reset()
        with self.assertRaises(ValueError) as error:
            data_object.create(
                {"name": "Optimus Prime"}, "class", "123", None, consistency_level="TWO"
            )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_called()

        reset()
        mock_obj = mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        data_object = DataObject(mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        check_error_message(self, error, requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_not_called()

        reset()
        mock_obj = mock_connection_func("post", status_code=204, return_json={})
        data_object = DataObject(mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        check_startswith_error_message(self, error, "Creating object")
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_not_called()

        reset()
        mock_obj = mock_connection_func(
            "post", status_code=204, return_json={"error": [{"message": "already exists"}]}
        )
        data_object = DataObject(mock_obj)
        with self.assertRaises(ObjectAlreadyExistsException) as error:
            data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        check_error_message(self, error, "None")
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_not_called()

        reset()
        mock_obj = mock_connection_func("post", status_code=204, return_json={})
        data_object = DataObject(mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.create({"name": "Alan Greenspan"}, "CoolestPersonEver")
        check_startswith_error_message(self, error, "Creating object")
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_not_called()

        # # test valid calls
        ## without vector argument
        connection_mock = mock_connection_func("post", return_json={"id": 0}, status_code=200)
        data_object = DataObject(connection_mock)

        object_ = {
            "lyrics": "da da dadadada dada, da da dadadada da, da da dadadada da, da da dadadada da Tequila"
        }
        class_name = "KaraokeSongs"
        vector = [1.0, 2.0]
        id_ = "ae6d51d6-b4ea-5a03-a808-6aae990bdebf"

        rest_object = {"class": class_name, "properties": object_, "id": id_}

        reset()
        uuid = data_object.create(object_, class_name, id_)
        self.assertEqual(uuid, "0")
        connection_mock.post.assert_called_with(
            path="/objects", weaviate_object=rest_object, params={}
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()
        mock_get_valid_uuid.assert_called()

        ## with vector argument
        connection_mock = mock_connection_func("post", return_json={"id": 0}, status_code=200)
        data_object = DataObject(connection_mock)

        object_ = {
            "lyrics": "da da dadadada dada, da da dadadada da, da da dadadada da, da da dadadada da Tequila"
        }
        class_name = "KaraokeSongs"
        vector = [1.0, 2.0]
        id_ = "ae6d51d6-b4ea-5a03-a808-6aae990bdebf"

        rest_object = {"class": class_name, "properties": object_, "vector": vector, "id": id_}

        reset()
        uuid = data_object.create(object_, class_name, id_, vector, "ALL")
        self.assertEqual(uuid, "0")
        connection_mock.post.assert_called_with(
            path="/objects", weaviate_object=rest_object, params={"consistency_level": "ALL"}
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()
        mock_get_valid_uuid.assert_called()

        reset()
        # uncapitalized class_names should be capitalized
        uuid = data_object.create(object_, "karaokeSongs", id_, vector)
        self.assertEqual(uuid, "0")
        connection_mock.post.assert_called_with(
            path="/objects", weaviate_object=rest_object, params={}
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()
        mock_get_valid_uuid.assert_called()

    @patch("weaviate.data.crud_data._get_dict_from_object", side_effect=lambda x: x)
    @patch("weaviate.data.crud_data.get_vector", side_effect=lambda x: x)
    def test_update(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `update` method.
        """
        uuid = "ae6d51d6-b4ea-5a03-a808-6aae990bdebf"
        data_object = DataObject(Mock())

        # error messages
        class_type_error_message = "Class must be type str"
        uuid_type_error_message = (
            lambda dt: f"'uuid' must be of type str or uuid.UUID, but was: {dt}"
        )
        uuid_value_error_message = "Not valid 'uuid' or 'uuid' can not be extracted from value"
        requests_error_message = "Object was not updated."
        unexpected_error_message = "Update of the object not successful"

        with self.assertRaises(ValueError) as error:
            data_object.update({"A": "B"}, "class", uuid, consistency_level="Unknown")
        check_error_message(self, error, "'Unknown' is not a valid ConsistencyLevel")
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(TypeError) as error:
            data_object.update({"A": "B"}, 35, uuid)
        check_error_message(self, error, class_type_error_message)
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(TypeError) as error:
            data_object.update({"A": "B"}, "Class", 1238234)
        check_error_message(self, error, uuid_type_error_message(int))
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(ValueError) as error:
            data_object.update({"A": "B"}, "Class", "NOT-A-valid-uuid")
        check_error_message(self, error, uuid_value_error_message)
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        mock_obj = mock_connection_func("patch", side_effect=RequestsConnectionError("Test!"))
        data_object = DataObject(mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.update(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                uuid,
            )
        check_error_message(self, error, requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(UnexpectedStatusCodeException) as error:
            mock_obj = mock_connection_func("patch", status_code=200, return_json={})
            data_object = DataObject(mock_obj)
            data_object.update(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                uuid,
            )
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test valid calls
        ## without vector argument
        connection_mock = mock_connection_func("patch", status_code=204)
        data_object = DataObject(connection_mock)
        data_object.update({"A": "B"}, "Class", uuid)
        weaviate_obj = {
            "id": uuid,
            "class": "Class",
            "properties": {"A": "B"},
        }
        connection_mock.patch.assert_called_with(
            path="/objects/ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            weaviate_object=weaviate_obj,
            params={},
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        ### with uncapitalized class_name
        connection_mock = mock_connection_func("patch", status_code=204)
        data_object = DataObject(connection_mock)
        data_object.update({"A": "B"}, "class", uuid)
        weaviate_obj = {
            "id": "ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            "class": "Class",
            "properties": {"A": "B"},
        }
        connection_mock.patch.assert_called_with(
            path="/objects/ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            weaviate_object=weaviate_obj,
            params={},
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        ## with vector argument
        connection_mock = mock_connection_func("patch", status_code=204)
        data_object = DataObject(connection_mock)
        data_object.update(
            {"A": "B"},
            "Class",
            uuid,
            vector=[2.0, 4.0],
            consistency_level=ConsistencyLevel.ONE,
        )
        weaviate_obj = {
            "id": uuid,
            "class": "Class",
            "properties": {"A": "B"},
            "vector": [2.0, 4.0],
        }
        connection_mock.patch.assert_called_with(
            path="/objects/ae6d51d6-b4ea-5a03-a808-6aae990bdebf",
            weaviate_object=weaviate_obj,
            params={"consistency_level": "ONE"},
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()

    @patch("weaviate.data.crud_data._get_dict_from_object", side_effect=lambda x: x)
    @patch("weaviate.data.crud_data.get_vector", side_effect=lambda x: x)
    def test_replace(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `replace` method.
        """
        uuid = "27be9d8d-1da1-4d52-821f-bc7e2a25247d"
        # test invalid consistency level
        data_object = DataObject(Mock)
        with self.assertRaises(ValueError) as error:
            data_object.replace(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
                consistency_level="Unknown",
            )
        mock_get_dict_from_object.assert_not_called()
        mock_get_vector.assert_not_called()

        # error messages
        requests_error_message = "Object was not replaced."
        unexpected_error_message = "Replace object"

        # test exceptions
        mock_obj = mock_connection_func("put", side_effect=RequestsConnectionError("Test!"))
        data_object = DataObject(mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.replace(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                uuid,
            )
        check_error_message(self, error, requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        mock_obj = mock_connection_func("put", status_code=204, return_json={})
        data_object = DataObject(mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.replace(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                uuid,
            )
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test valid calls
        ## without vector argument
        connection_mock = mock_connection_func("put")
        data_object = DataObject(connection_mock)
        data_object.replace({"A": 2}, "Hero", uuid)
        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
        }
        connection_mock.put.assert_called_with(
            path="/objects/27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            weaviate_object=weaviate_obj,
            params={},
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        ### with uncapitalized class_name
        connection_mock = mock_connection_func("put")
        data_object = DataObject(connection_mock)
        data_object.replace({"A": 2}, "hero", uuid)
        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
        }
        connection_mock.put.assert_called_with(
            path="/objects/27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            weaviate_object=weaviate_obj,
            params={},
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # with vector argument
        connection_mock = mock_connection_func("put")
        data_object = DataObject(connection_mock)
        data_object.replace(
            {"A": 2},
            "Hero",
            uuid,
            vector=[3.0, 5, 7],
            consistency_level="ONE",
        )
        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
            "vector": [3.0, 5, 7],
        }
        connection_mock.put.assert_called_with(
            path="/objects/27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            weaviate_object=weaviate_obj,
            params={"consistency_level": "ONE"},
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_called()

    def test_delete(self):
        """
        Test the `delete` method.
        """
        uuid = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        connection_mock = Mock()
        connection_mock.server_version = "1.13.2"
        data_object = DataObject(connection_mock)

        # error messages
        uuid_type_error_message = (
            lambda dt: f"'uuid' must be of type str or uuid.UUID, but was: {dt}"
        )
        uuid_value_error_message = "Not valid 'uuid' or 'uuid' can not be extracted from value"
        requests_error_message = "Object could not be deleted."
        unexpected_error_message = "Delete object"

        with self.assertRaises(TypeError) as error:
            data_object.delete(4)
        check_error_message(self, error, uuid_type_error_message(int))

        with self.assertRaises(ValueError) as error:
            data_object.delete("Hallo World")
        check_error_message(self, error, uuid_value_error_message)

        ## test invalid consistency level
        with self.assertRaises(ValueError) as error:
            data_object.delete(uuid=uuid, consistency_level="Unknown")

        connection_mock = mock_connection_func(
            "delete", side_effect=RequestsConnectionError("Test!")
        )
        data_object = DataObject(connection_mock)
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
        check_error_message(self, error, requests_error_message)

        connection_mock = mock_connection_func("delete", status_code=405)
        data_object = DataObject(connection_mock)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
        check_startswith_error_message(self, error, unexpected_error_message)

        # 1. Successfully delete something
        connection_mock = mock_connection_func("delete", status_code=204)
        data_object = DataObject(connection_mock)

        object_id = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        data_object.delete(object_id)
        connection_mock.delete.assert_called_with(
            path="/objects/" + object_id,
            params={},
        )

        data_object.delete(object_id, None, ConsistencyLevel.ALL)
        connection_mock.delete.assert_called_with(
            path="/objects/" + object_id,
            params={"consistency_level": "ALL"},
        )

    def test_get_by_id(self):
        """
        Test the `get_by_id` method.
        """

        data_object = DataObject(Mock())

        mock_get = Mock(return_value="Test")
        data_object.get = mock_get
        data_object.get_by_id(
            uuid="UUID", additional_properties=["Test", "Array"], with_vector=True
        )
        mock_get.assert_called_with(
            uuid="UUID",
            class_name=None,
            additional_properties=["Test", "Array"],
            with_vector=True,
            node_name=None,
            consistency_level=None,
            tenant=None,
        )

        data_object.get_by_id(uuid="UUID2", additional_properties=["Test"], with_vector=False)
        mock_get.assert_called_with(
            uuid="UUID2",
            class_name=None,
            additional_properties=["Test"],
            with_vector=False,
            node_name=None,
            consistency_level=None,
            tenant=None,
        )

        data_object.get_by_id(
            uuid="UUID3",
            additional_properties=["Test"],
            with_vector=False,
            consistency_level=ConsistencyLevel.QUORUM,
        )
        mock_get.assert_called_with(
            uuid="UUID3",
            class_name=None,
            additional_properties=["Test"],
            with_vector=False,
            node_name=None,
            consistency_level=ConsistencyLevel.QUORUM,
            tenant=None,
        )

        data_object.get_by_id(
            uuid="UUID4", additional_properties=["Test"], with_vector=False, node_name="node1"
        )
        mock_get.assert_called_with(
            uuid="UUID4",
            class_name=None,
            additional_properties=["Test"],
            with_vector=False,
            node_name="node1",
            consistency_level=None,
            tenant=None,
        )

        connection_mock = Mock()
        connection_mock.server_version = "1.17.0"
        data_object = DataObject(connection_mock)
        with self.assertRaises(ValueError) as error:
            data_object.get_by_id(
                uuid="UUID4",
                class_name="SomeClass",
                additional_properties=["Test"],
                with_vector=False,
                consistency_level=12345,
            )
            assert "123" in error
        with self.assertRaises(ValueError) as error:
            data_object.get_by_id(
                uuid="UUID4",
                class_name="SomeClass",
                additional_properties=["Test"],
                with_vector=False,
                consistency_level="all",
            )
            assert "all" in error
        with self.assertRaises(ValueError) as error:
            data_object.get_by_id(
                uuid="UUID4",
                class_name="SomeClass",
                additional_properties=["Test"],
                with_vector=False,
                consistency_level={"consistency_level": "ALL"},
            )
            assert "consistency_level" in error

    @patch("weaviate.data.crud_data._get_params")
    def test_get(self, mock_get_params):
        """
        Test the `get` method.
        """

        # error messages
        requests_error_message = "Could not get object/s."
        unexpected_error_message = "Get object/s"

        # test exceptions

        data_object = DataObject(
            mock_connection_func("get", side_effect=RequestsConnectionError("Test!"))
        )
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.get()
        check_error_message(self, error, requests_error_message)

        data_object = DataObject(mock_connection_func("get", status_code=405))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.get()
        check_startswith_error_message(self, error, unexpected_error_message)

        # test valid calls
        return_value_get = {"my_key": 12341}
        mock_get_params.return_value = {"include": "test1,test2"}
        connection_mock = mock_connection_func("get", return_json=return_value_get, status_code=200)
        data_object = DataObject(connection_mock)
        result = data_object.get()
        self.assertEqual(result, return_value_get)
        connection_mock.get.assert_called_with(path="/objects", params={"include": "test1,test2"})

        return_value_get = {"my_key": "12341"}
        mock_get_params.return_value = {"include": "test1,test2"}
        connection_mock = mock_connection_func("get", return_json=return_value_get, status_code=200)
        data_object = DataObject(connection_mock)
        result = data_object.get(uuid="1d420c9c98cb11ec9db61e008a366d49")
        self.assertEqual(result, return_value_get)
        connection_mock.get.assert_called_with(
            path="/objects/1d420c9c-98cb-11ec-9db6-1e008a366d49", params={"include": "test1,test2"}
        )

    def test_exists(self):
        """
        Test the `exists` method.
        """
        uuid = "1d420c9c-98cb-11ec-9db6-1e008a366d49"
        # error messages
        requests_error_message = "Could not check if object exist."
        unexpected_error_message = "Object exists"

        # test exceptions
        data_object = DataObject(mock_connection_func("head"))
        with self.assertRaises(ValueError) as error:
            data_object.exists(uuid=uuid, consistency_level="Unknown")

        data_object = DataObject(
            mock_connection_func("head", side_effect=RequestsConnectionError("Test!"))
        )
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.exists(uuid="1d420c9c98cb11ec9db61e008a366d49")
        check_error_message(self, error, requests_error_message)

        data_object = DataObject(mock_connection_func("head", status_code=200))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.exists(uuid="1d420c9c98cb11ec9db61e008a366d49")
        check_startswith_error_message(self, error, unexpected_error_message)

        # test valid calls
        connection_mock = mock_connection_func("head", status_code=204)
        data_object = DataObject(connection_mock)
        result = data_object.exists(uuid="1d420c9c98cb11ec9db61e008a366d49")
        self.assertEqual(result, True)
        connection_mock.head.assert_called_with(
            path="/objects/1d420c9c-98cb-11ec-9db6-1e008a366d49",
            params={},
        )

        connection_mock = mock_connection_func("head", status_code=404)
        data_object = DataObject(connection_mock)
        result = data_object.exists(uuid, None, ConsistencyLevel.QUORUM)
        self.assertEqual(result, False)
        connection_mock.head.assert_called_with(
            path="/objects/1d420c9c-98cb-11ec-9db6-1e008a366d49",
            params={"consistency_level": "QUORUM"},
        )

    @patch("weaviate.data.crud_data._get_dict_from_object", side_effect=lambda x: x)
    @patch("weaviate.data.crud_data.get_vector", side_effect=lambda x: x)
    def test_validate(self, mock_get_vector, mock_get_dict_from_object):
        """
        Test the `validate` method.
        """

        data_object = DataObject(Mock())

        # error messages
        uuid_type_error_message = (
            lambda dt: f"'uuid' must be of type str or uuid.UUID, but was: {dt}"
        )
        class_name_error_message = lambda dt: f"Expected class_name of type `str` but was: {dt}"
        requests_error_message = "Object was not validated against Weaviate."
        unexpected_error_message = "Validate object"

        # test exceptions
        with self.assertRaises(TypeError) as error:
            data_object.validate({}, "Name", 1)
        check_error_message(self, error, uuid_type_error_message(int))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        with self.assertRaises(TypeError) as error:
            data_object.validate({}, ["Name"], "73802305-c0da-427e-b21c-d6779a22f35f")
        check_error_message(self, error, class_name_error_message(list))
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        data_object = DataObject(
            mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        )
        with self.assertRaises(RequestsConnectionError) as error:
            data_object.validate(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "73802305-c0da-427e-b21c-d6779a22f35f",
            )
        check_error_message(self, error, requests_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        data_object = DataObject(mock_connection_func("post", status_code=204, return_json={}))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            data_object.validate(
                {"name": "Alan Greenspan"},
                "CoolestPersonEver",
                "73802305-c0da-427e-b21c-d6779a22f35f",
            )
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test valid calls
        # test for status_code 200 without vector argument
        connection_mock = mock_connection_func("post", status_code=200)
        data_object = DataObject(connection_mock)

        response = data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {"error": None, "valid": True})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
        }
        connection_mock.post.assert_called_with(
            path="/objects/validate", weaviate_object=weaviate_obj
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        ### with uncapitalized class_name
        connection_mock = mock_connection_func("post", status_code=200)
        data_object = DataObject(connection_mock)

        response = data_object.validate({"A": 2}, "hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {"error": None, "valid": True})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
        }
        connection_mock.post.assert_called_with(
            path="/objects/validate", weaviate_object=weaviate_obj
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test for status_code 422
        connection_mock = mock_connection_func(
            "post", status_code=422, return_json={"error": "Not OK!"}
        )
        data_object = DataObject(connection_mock)

        response = data_object.validate({"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d")
        self.assertEqual(response, {"error": "Not OK!", "valid": False})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
        }
        connection_mock.post.assert_called_with(
            path="/objects/validate", weaviate_object=weaviate_obj
        )
        mock_get_dict_from_object.assert_called()
        mock_get_vector.assert_not_called()

        # test for status_code 200 with vector argument
        connection_mock = mock_connection_func("post", status_code=200)
        data_object = DataObject(connection_mock)

        response = data_object.validate(
            {"A": 2}, "Hero", "27be9d8d-1da1-4d52-821f-bc7e2a25247d", vector=[-9.8, 6.66]
        )
        self.assertEqual(response, {"error": None, "valid": True})

        weaviate_obj = {
            "id": "27be9d8d-1da1-4d52-821f-bc7e2a25247d",
            "class": "Hero",
            "properties": {"A": 2},
            "vector": [-9.8, 6.66],
        }
        connection_mock.post.assert_called_with(
            path="/objects/validate", weaviate_object=weaviate_obj
        )
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
        check_error_message(self, error, type_error_message(str))

        self.assertEqual(_get_params(["test1", "test2"], False), {"include": "test1,test2"})
        self.assertEqual(_get_params(None, True), {"include": "vector"})
        self.assertEqual(_get_params([], True), {"include": "vector"})
        self.assertEqual(_get_params(["test1", "test2"], True), {"include": "test1,test2,vector"})

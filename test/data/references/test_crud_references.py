import unittest
from unittest.mock import Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.data.references import Reference
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException


class TestReference(unittest.TestCase):
    def setUp(self):
        self.uuid_1 = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        self.uuid_2 = "a36268d4-a6b5-5274-985f-45f13ce0c642"
        self.uuid_error_message = f"'uuid' must be of type str or uuid.UUID, but was: {int}"
        self.valid_uuid_error_message = "Not valid 'uuid' or 'uuid' can not be extracted from value"
        self.name_error_message = (
            lambda p: f"'from_property_name' must be of type 'str'. Given type: {p}"
        )

    def test_delete(self):
        """
        Test `delete` method`.
        """

        connection_mock = Mock()
        connection_mock.server_version = "1.13.2"
        reference = Reference(connection_mock)

        # error messages
        unexpected_error_msg = "Delete property reference to object"
        connection_error_msg = "Reference was not deleted."

        # invalid calls
        with self.assertRaises(TypeError) as error:
            reference.delete(1, "myProperty", self.uuid_2)
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(TypeError) as error:
            reference.delete(self.uuid_1, "myProperty", 2)
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(TypeError) as error:
            reference.delete(self.uuid_1, 3, self.uuid_2)
        check_error_message(self, error, self.name_error_message(int))

        with self.assertRaises(ValueError) as error:
            reference.delete("str", "myProperty", self.uuid_2)
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.delete(self.uuid_1, "myProperty", "str")
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.delete(self.uuid_1, "myProperty", self.uuid_2, consistency_level=1)

        mock_obj = mock_connection_func("delete", status_code=200)
        reference = Reference(mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            reference.delete(self.uuid_1, "myProperty", self.uuid_2)
        check_startswith_error_message(self, error, unexpected_error_msg)

        mock_obj = mock_connection_func("delete", side_effect=RequestsConnectionError("Test!"))
        reference = Reference(mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            reference.delete(self.uuid_1, "myProperty", self.uuid_2)
        check_error_message(self, error, connection_error_msg)

        # test valid calls
        connection_mock = mock_connection_func("delete", status_code=204)
        reference = Reference(connection_mock)

        reference.delete(self.uuid_1, "myProperty", self.uuid_2)

        connection_mock.delete.assert_called_with(
            path=f"/objects/{self.uuid_1}/references/myProperty",
            weaviate_object={"beacon": f"weaviate://localhost/{self.uuid_2}"},
            params={},
        )

        reference.delete(
            self.uuid_1,
            "hasItem",
            f"http://localhost:8080/v1/objects/{self.uuid_2}",
            consistency_level="ONE",
        )

        connection_mock.delete.assert_called_with(
            path=f"/objects/{self.uuid_1}/references/hasItem",
            weaviate_object={"beacon": f"weaviate://localhost/{self.uuid_2}"},
            params={"consistency_level": "ONE"},
        )

    def test_add(self):
        """
        Test the `add` method.
        """

        connection_mock = Mock()
        connection_mock.server_version = "1.13.2"
        reference = Reference(connection_mock)

        # error messages
        unexpected_error_msg = "Add property reference to object"
        connection_error_msg = "Reference was not added."

        # test exceptions
        with self.assertRaises(TypeError) as error:
            reference.add(1, "prop", self.uuid_1)
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(TypeError) as error:
            reference.add(self.uuid_1, 1, self.uuid_2)
        check_error_message(self, error, self.name_error_message(int))

        with self.assertRaises(TypeError) as error:
            reference.add(self.uuid_1, "prop", 1)
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.add("my UUID", "prop", self.uuid_2)
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.add(self.uuid_1, "prop", "my uuid")
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.add(self.uuid_1, "prop", self.uuid_2, consistency_level=1)

        with self.assertRaises(ValueError) as error:
            reference.add(
                f"http://localhost:8080/v1/objects/{self.uuid_1}",
                "prop",
                "http://localhost:8080/v1/objects/MY_UUID",
            )
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.add(
                "http://localhost:8080/v1/objects/My-UUID",
                "prop",
                f"http://localhost:8080/v1/objects/{self.uuid_2}",
            )
        check_error_message(self, error, self.valid_uuid_error_message)

        mock_obj = mock_connection_func("post", status_code=204)
        reference = Reference(mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            reference.add(self.uuid_1, "myProperty", self.uuid_2)
        check_startswith_error_message(self, error, unexpected_error_msg)

        mock_obj = mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        reference = Reference(mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            reference.add(self.uuid_1, "myProperty", self.uuid_2)
        check_error_message(self, error, connection_error_msg)

        # test valid calls
        connection_mock = mock_connection_func("post")
        reference = Reference(connection_mock)

        # 1. Plain
        reference.add(
            "3250b0b8-eaf7-499b-ac68-9084c9c82d0f",
            "hasItem",
            "99725f35-f12a-4f36-a2e2-0d41501f4e0e",
        )
        connection_mock.post.assert_called_with(
            path="/objects/3250b0b8-eaf7-499b-ac68-9084c9c82d0f/references/hasItem",
            weaviate_object={"beacon": "weaviate://localhost/99725f35-f12a-4f36-a2e2-0d41501f4e0e"},
            params={},
        )

        # 2. using url
        reference.add(
            "http://localhost:8080/v1/objects/7591be77-5959-4386-9828-423fc5096e87",
            "hasItem",
            "http://localhost:8080/v1/objects/1cd80c11-29f0-453f-823c-21547b1511f0",
        )
        connection_mock.post.assert_called_with(
            path="/objects/7591be77-5959-4386-9828-423fc5096e87/references/hasItem",
            weaviate_object={"beacon": "weaviate://localhost/1cd80c11-29f0-453f-823c-21547b1511f0"},
            params={},
        )

        # 3. using weaviate url
        reference.add(
            "weaviate://localhost/f8def983-87e7-4e21-bf10-e32e2de3efcf",
            "hasItem",
            "weaviate://localhost/e40aaef5-d3e5-44f1-8ec4-3eafc8475078",
            consistency_level="ALL",
        )
        connection_mock.post.assert_called_with(
            path="/objects/f8def983-87e7-4e21-bf10-e32e2de3efcf/references/hasItem",
            weaviate_object={"beacon": "weaviate://localhost/e40aaef5-d3e5-44f1-8ec4-3eafc8475078"},
            params={"consistency_level": "ALL"},
        )

    def test_update(self):
        """
        Test the `update` method.
        """

        connection_mock = Mock()
        connection_mock.server_version = "1.13.2"
        reference = Reference(connection_mock)

        # error messages
        unexpected_error_msg = "Update property reference to object"
        connection_error_msg = "Reference was not updated."

        # test exceptions
        with self.assertRaises(TypeError) as error:
            reference.update(1, "prop", [self.uuid_1])
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(TypeError) as error:
            reference.update(self.uuid_1, 1, [self.uuid_2])
        check_error_message(self, error, self.name_error_message(int))

        with self.assertRaises(TypeError) as error:
            reference.update(self.uuid_1, "prop", 1)
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(TypeError) as error:
            reference.update(self.uuid_1, "prop", [1])
        check_error_message(self, error, self.uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.update("my UUID", "prop", self.uuid_2)
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.update(self.uuid_1, "prop", "my uuid")
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.update(self.uuid_1, "prop", ["my uuid"])
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.update(self.uuid_1, "prop", self.uuid_2, consistency_level=1)
        check_error_message(self, error, "1 is not a valid ConsistencyLevel")

        with self.assertRaises(ValueError) as error:
            reference.update(
                f"http://localhost:8080/v1/objects/{self.uuid_1}",
                "prop",
                "http://localhost:8080/v1/objects/MY_UUID",
            )
        check_error_message(self, error, self.valid_uuid_error_message)

        with self.assertRaises(ValueError) as error:
            reference.update(
                "http://localhost:8080/v1/objects/My-UUID",
                "prop",
                f"http://localhost:8080/v1/objects/{self.uuid_2}",
            )
        check_error_message(self, error, self.valid_uuid_error_message)

        mock_obj = mock_connection_func("put", status_code=204)
        reference = Reference(mock_obj)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            reference.update(self.uuid_1, "myProperty", self.uuid_2)
        check_startswith_error_message(self, error, unexpected_error_msg)

        mock_obj = mock_connection_func("put", side_effect=RequestsConnectionError("Test!"))
        reference = Reference(mock_obj)
        with self.assertRaises(RequestsConnectionError) as error:
            reference.update(self.uuid_1, "myProperty", self.uuid_2)
        check_error_message(self, error, connection_error_msg)

        # test valid calls
        connection_mock = mock_connection_func("put")
        reference = Reference(connection_mock)

        reference.update(
            "de998e81-fa66-440e-a1de-2a2013667e77",
            "hasAwards",
            "fc041624-4ddf-4b76-8e09-a5b0b9f9f832",
        )
        connection_mock.put.assert_called_with(
            path="/objects/de998e81-fa66-440e-a1de-2a2013667e77/references/hasAwards",
            weaviate_object=[
                {"beacon": "weaviate://localhost/fc041624-4ddf-4b76-8e09-a5b0b9f9f832"}
            ],
            params={},
        )

        reference.update(
            "4e44db9b-7f9c-4cf4-a3a0-b57024eefed0",
            "hasAwards",
            [
                "17ee17bd-a09a-49ff-adeb-d242f25f390d",
                "f8c25386-707c-40c0-b7b9-26cc0e9b2bd1",
                "d671dc52-dce4-46e7-8731-b722f19420c8",
            ],
            consistency_level=ConsistencyLevel.QUORUM,
        )
        connection_mock.put.assert_called_with(
            path="/objects/4e44db9b-7f9c-4cf4-a3a0-b57024eefed0/references/hasAwards",
            weaviate_object=[
                {"beacon": "weaviate://localhost/17ee17bd-a09a-49ff-adeb-d242f25f390d"},
                {"beacon": "weaviate://localhost/f8c25386-707c-40c0-b7b9-26cc0e9b2bd1"},
                {"beacon": "weaviate://localhost/d671dc52-dce4-46e7-8731-b722f19420c8"},
            ],
            params={"consistency_level": "QUORUM"},
        )

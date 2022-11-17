import unittest
from unittest.mock import patch

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.backup.backup import Backup, STORAGE_NAMES
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    BackupFailedException,
)


class TestBackup(unittest.TestCase):
    @patch("weaviate.backup.backup.Backup.get_create_status")
    def test_create(self, mock_status):
        """
        Test the `create` method.
        """

        # error messages
        backup_type_err_msg = lambda dt: f"'backup_id' must be of type str. Given type: {dt}."
        storage_val_err_msg = lambda val: (
            f"'backend' must have one of these values: {STORAGE_NAMES}. " f"Given value: {val}."
        )
        include_type_err_msg = lambda dt: (
            "'include_classes' must be of type str, list of str or None. " f"Given type: {dt}."
        )
        exclude_type_err_msg = lambda dt: (
            "'exclude_classes' must be of type str, list of str or None. " f"Given type: {dt}."
        )
        wait_type_err_msg = lambda dt: (
            f"'wait_for_completion' must be of type bool. Given type: {dt}."
        )
        include_exclude_err_msg = (
            "Either 'include_classes' OR 'exclude_classes' can be set, not both."
        )
        connection_err_msg = "Backup creation failed due to connection error."
        status_code_err_msg = "Backup creation"
        backup_failed_err_msg = lambda status: f"Backup failed: {status}"

        # invalid calls

        with self.assertRaises(TypeError) as error:
            Backup(None).create(
                backup_id=b"My-bucket",
                backend="s3",
            )
        check_error_message(self, error, backup_type_err_msg(bytes))

        with self.assertRaises(ValueError) as error:
            Backup(None).create(
                backup_id="My-bucket",
                backend=b"s3",
            )
        check_error_message(self, error, storage_val_err_msg(b"s3"))

        with self.assertRaises(ValueError) as error:
            Backup(None).create(
                backup_id="My-bucket",
                backend="s4",
            )
        check_error_message(self, error, storage_val_err_msg("s4"))

        with self.assertRaises(TypeError) as error:
            Backup(None).create(
                backup_id="My-bucket",
                backend="s3",
                include_classes=b"MyClass",
            )
        check_error_message(self, error, include_type_err_msg(bytes))

        with self.assertRaises(TypeError) as error:
            Backup(None).create(
                backup_id="My-bucket",
                backend="s3",
                exclude_classes=b"MyClass",
            )
        check_error_message(self, error, exclude_type_err_msg(bytes))

        with self.assertRaises(TypeError) as error:
            Backup(None).create(
                backup_id="My-bucket",
                backend="s3",
                include_classes="MyClass1",
                exclude_classes="MyClass2",
            )
        check_error_message(self, error, include_exclude_err_msg)

        with self.assertRaises(TypeError) as error:
            Backup(None).create(
                backup_id="My-bucket",
                backend="s3",
                include_classes="MyClass1",
                exclude_classes=[],
                wait_for_completion=0,
            )
        check_error_message(self, error, wait_type_err_msg(int))

        mock_conn = mock_connection_func("post", side_effect=RequestsConnectionError)
        with self.assertRaises(RequestsConnectionError) as error:
            Backup(mock_conn).create(
                backup_id="My-bucket",
                backend="s3",
            )
        check_error_message(self, error, connection_err_msg)

        mock_conn = mock_connection_func("post", status_code=404)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Backup(mock_conn).create(
                backup_id="My-bucket",
                backend="s3",
            )
        check_startswith_error_message(self, error, status_code_err_msg)

        mock_conn = mock_connection_func(
            "post", status_code=200, return_json={"classes": ["Test"], "error": "Test2"}
        )
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        with self.assertRaises(BackupFailedException) as error:
            Backup(mock_conn).create(
                backup_id="My-bucket",
                backend="s3",
                wait_for_completion=True,
            )
        check_error_message(
            self,
            error,
            backup_failed_err_msg({"classes": ["Test"], "error": "test", "status": "FAILED"}),
        )

        # valid calls
        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).create(
            backup_id="My-Bucket",
            backend="s3",
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/s3",
            weaviate_object={
                "id": "my-bucket",
                "config": {},
                "include": [],
                "exclude": [],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).create(
            backup_id="My-Bucket", backend="gcs", include_classes="myClass"
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/gcs",
            weaviate_object={
                "id": "my-bucket",
                "config": {},
                "include": ["MyClass"],
                "exclude": [],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).create(
            backup_id="My-Bucket", backend="filesystem", include_classes=["class1", "Class2"]
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/filesystem",
            weaviate_object={
                "id": "my-bucket",
                "config": {},
                "include": ["Class1", "Class2"],
                "exclude": [],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).create(
            backup_id="My-Bucket",
            backend="s3",
            exclude_classes="myClass",
            include_classes=None,
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/s3",
            weaviate_object={
                "id": "my-bucket",
                "config": {},
                "include": [],
                "exclude": ["MyClass"],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).create(
            backup_id="My-Bucket",
            backend="s3",
            exclude_classes=["class1", "Class2"],
            include_classes=[],
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/s3",
            weaviate_object={
                "id": "my-bucket",
                "config": {},
                "include": [],
                "exclude": ["Class1", "Class2"],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "SUCCESS"}
        result = Backup(mock_conn).create(
            backup_id="My-Bucket2",
            backend="s3",
            wait_for_completion=True,
        )
        self.assertDictEqual(result, {"status": "SUCCESS"})
        mock_conn.post.assert_called_with(
            path="/backups/s3",
            weaviate_object={
                "id": "my-bucket2",
                "config": {},
                "include": [],
                "exclude": [],
            },
        )

        with patch("weaviate.backup.backup.sleep") as mock_sleep:

            def override_mock_status():
                mock_status.return_value = {"status": "SUCCESS"}

            mock_sleep.side_effect = lambda n: override_mock_status()
            mock_conn = mock_connection_func(
                "post", status_code=200, return_json={"status": "TEST"}
            )
            mock_status.return_value = {"status": "TRANSFERRING"}
            result = Backup(mock_conn).create(
                backup_id="my-Bucket_2",
                backend="gcs",
                wait_for_completion=True,
            )
            self.assertDictEqual(result, {"status": "SUCCESS"})
            mock_conn.post.assert_called_with(
                path="/backups/gcs",
                weaviate_object={
                    "id": "my-bucket_2",
                    "config": {},
                    "include": [],
                    "exclude": [],
                },
            )

    def test_get_create_status(self):
        """
        Test the `get_create_status` method.
        """

        # error messages
        backup_type_err_msg = lambda dt: f"'backup_id' must be of type str. Given type: {dt}."
        storage_val_err_msg = lambda val: (
            f"'backend' must have one of these values: {STORAGE_NAMES}. " f"Given value: {val}."
        )
        connection_err_msg = "Backup creation status failed due to connection error."
        status_code_err_msg = "Backup status check"

        # invalid calls
        with self.assertRaises(TypeError) as error:
            Backup(None).get_create_status(
                backup_id=b"My-bucket",
                backend="s3",
            )
        check_error_message(self, error, backup_type_err_msg(bytes))

        with self.assertRaises(ValueError) as error:
            Backup(None).get_create_status(
                backup_id="My-bucket",
                backend=b"s3",
            )
        check_error_message(self, error, storage_val_err_msg(b"s3"))

        with self.assertRaises(ValueError) as error:
            Backup(None).get_create_status(
                backup_id="My-bucket",
                backend="s4",
            )
        check_error_message(self, error, storage_val_err_msg("s4"))

        mock_conn = mock_connection_func("get", side_effect=RequestsConnectionError)
        with self.assertRaises(RequestsConnectionError) as error:
            Backup(mock_conn).get_create_status(
                backup_id="My-bucket",
                backend="s3",
            )
        check_error_message(self, error, connection_err_msg)

        mock_conn = mock_connection_func("get", status_code=404)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Backup(mock_conn).get_create_status(
                backup_id="My-bucket",
                backend="s3",
            )
        check_startswith_error_message(self, error, status_code_err_msg)

        # valid calls

        mock_conn = mock_connection_func("get", status_code=200, return_json={"status": "TEST"})
        result = Backup(mock_conn).get_create_status(
            backup_id="My-Bucket",
            backend="s3",
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.get.assert_called_with(
            path="/backups/s3/my-bucket",
        )

        mock_conn = mock_connection_func(
            "get", status_code=200, return_json={"status": "TEST", "error": None}
        )
        result = Backup(mock_conn).get_create_status(
            backup_id="My-Bucket",
            backend="gcs",
        )
        self.assertDictEqual(result, {"status": "TEST", "error": None})
        mock_conn.get.assert_called_with(
            path="/backups/gcs/my-bucket",
        )

        mock_conn = mock_connection_func("get", status_code=200, return_json={"status": "TEST2"})
        result = Backup(mock_conn).get_create_status(
            backup_id="My-Bucket123",
            backend="filesystem",
        )
        self.assertDictEqual(result, {"status": "TEST2"})
        mock_conn.get.assert_called_with(
            path="/backups/filesystem/my-bucket123",
        )

    @patch("weaviate.backup.backup.Backup.get_restore_status")
    def test_restore(self, mock_status):
        """
        Test the `create` method.
        """

        # error messages
        backup_type_err_msg = lambda dt: f"'backup_id' must be of type str. Given type: {dt}."
        storage_val_err_msg = lambda val: (
            f"'backend' must have one of these values: {STORAGE_NAMES}. " f"Given value: {val}."
        )
        include_type_err_msg = lambda dt: (
            "'include_classes' must be of type str, list of str or None. " f"Given type: {dt}."
        )
        exclude_type_err_msg = lambda dt: (
            "'exclude_classes' must be of type str, list of str or None. " f"Given type: {dt}."
        )
        wait_type_err_msg = lambda dt: (
            f"'wait_for_completion' must be of type bool. Given type: {dt}."
        )
        include_exclude_err_msg = (
            "Either 'include_classes' OR 'exclude_classes' can be set, not both."
        )
        connection_err_msg = "Backup restore failed due to connection error."
        status_code_err_msg = "Backup restore"
        backup_failed_err_msg = lambda status: f"Backup restore failed: {status}"

        # invalid calls

        with self.assertRaises(TypeError) as error:
            Backup(None).restore(
                backup_id=b"My-bucket",
                backend="s3",
            )
        check_error_message(self, error, backup_type_err_msg(bytes))

        with self.assertRaises(ValueError) as error:
            Backup(None).restore(
                backup_id="My-bucket",
                backend=b"s3",
            )
        check_error_message(self, error, storage_val_err_msg(b"s3"))

        with self.assertRaises(ValueError) as error:
            Backup(None).restore(
                backup_id="My-bucket",
                backend="s4",
            )
        check_error_message(self, error, storage_val_err_msg("s4"))

        with self.assertRaises(TypeError) as error:
            Backup(None).restore(
                backup_id="My-bucket",
                backend="s3",
                include_classes=b"MyClass",
            )
        check_error_message(self, error, include_type_err_msg(bytes))

        with self.assertRaises(TypeError) as error:
            Backup(None).restore(
                backup_id="My-bucket",
                backend="s3",
                exclude_classes=b"MyClass",
            )
        check_error_message(self, error, exclude_type_err_msg(bytes))

        with self.assertRaises(TypeError) as error:
            Backup(None).restore(
                backup_id="My-bucket",
                backend="s3",
                include_classes="MyClass1",
                exclude_classes="MyClass2",
            )
        check_error_message(self, error, include_exclude_err_msg)

        with self.assertRaises(TypeError) as error:
            Backup(None).restore(
                backup_id="My-bucket",
                backend="s3",
                include_classes="MyClass1",
                exclude_classes=[],
                wait_for_completion=0,
            )
        check_error_message(self, error, wait_type_err_msg(int))

        mock_conn = mock_connection_func("post", side_effect=RequestsConnectionError)
        with self.assertRaises(RequestsConnectionError) as error:
            Backup(mock_conn).restore(
                backup_id="My-bucket",
                backend="s3",
            )
        check_error_message(self, error, connection_err_msg)

        mock_conn = mock_connection_func("post", status_code=404)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Backup(mock_conn).restore(
                backup_id="My-bucket",
                backend="s3",
            )
        check_startswith_error_message(self, error, status_code_err_msg)

        mock_conn = mock_connection_func(
            "post", status_code=200, return_json={"classes": ["Test"], "error": "Test2"}
        )
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        with self.assertRaises(BackupFailedException) as error:
            Backup(mock_conn).restore(
                backup_id="My-bucket",
                backend="s3",
                wait_for_completion=True,
            )
        check_error_message(
            self,
            error,
            backup_failed_err_msg({"classes": ["Test"], "error": "test", "status": "FAILED"}),
        )

        # valid calls
        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).restore(
            backup_id="My-Bucket",
            backend="s3",
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/s3/my-bucket/restore",
            weaviate_object={
                "config": {},
                "include": [],
                "exclude": [],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).restore(
            backup_id="My-Bucket", backend="gcs", include_classes="myClass"
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/gcs/my-bucket/restore",
            weaviate_object={
                "config": {},
                "include": ["MyClass"],
                "exclude": [],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).restore(
            backup_id="My-Bucket", backend="filesystem", include_classes=["class1", "Class2"]
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/filesystem/my-bucket/restore",
            weaviate_object={
                "config": {},
                "include": ["Class1", "Class2"],
                "exclude": [],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).restore(
            backup_id="My-Bucket",
            backend="s3",
            exclude_classes="myClass",
            include_classes=None,
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/s3/my-bucket/restore",
            weaviate_object={
                "config": {},
                "include": [],
                "exclude": ["MyClass"],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "FAILED", "error": "test"}
        result = Backup(mock_conn).restore(
            backup_id="My-Bucket",
            backend="s3",
            exclude_classes=["class1", "Class2"],
            include_classes=[],
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.post.assert_called_with(
            path="/backups/s3/my-bucket/restore",
            weaviate_object={
                "config": {},
                "include": [],
                "exclude": ["Class1", "Class2"],
            },
        )

        mock_conn = mock_connection_func("post", status_code=200, return_json={"status": "TEST"})
        mock_status.return_value = {"status": "SUCCESS"}
        result = Backup(mock_conn).restore(
            backup_id="My-Bucket2",
            backend="s3",
            wait_for_completion=True,
        )
        self.assertDictEqual(result, {"status": "SUCCESS"})
        mock_conn.post.assert_called_with(
            path="/backups/s3/my-bucket2/restore",
            weaviate_object={
                "config": {},
                "include": [],
                "exclude": [],
            },
        )

        with patch("weaviate.backup.backup.sleep") as mock_sleep:

            def override_mock_status():
                mock_status.return_value = {"status": "SUCCESS"}

            mock_sleep.side_effect = lambda n: override_mock_status()
            mock_conn = mock_connection_func(
                "post", status_code=200, return_json={"status": "TEST"}
            )
            mock_status.return_value = {"status": "TRANSFERRING"}
            result = Backup(mock_conn).restore(
                backup_id="my-Bucket_2",
                backend="gcs",
                wait_for_completion=True,
            )
            self.assertDictEqual(result, {"status": "SUCCESS"})
            mock_conn.post.assert_called_with(
                path="/backups/gcs/my-bucket_2/restore",
                weaviate_object={
                    "config": {},
                    "include": [],
                    "exclude": [],
                },
            )

    def test_get_restore_status(self):
        """
        Test the `get_restore_status` method.
        """

        # error messages
        backup_type_err_msg = lambda dt: f"'backup_id' must be of type str. Given type: {dt}."
        storage_val_err_msg = lambda val: (
            f"'backend' must have one of these values: {STORAGE_NAMES}. " f"Given value: {val}."
        )
        connection_err_msg = "Backup restore status failed due to connection error."
        status_code_err_msg = "Backup restore status check"

        # invalid calls
        with self.assertRaises(TypeError) as error:
            Backup(None).get_restore_status(
                backup_id=b"My-bucket",
                backend="s3",
            )
        check_error_message(self, error, backup_type_err_msg(bytes))

        with self.assertRaises(ValueError) as error:
            Backup(None).get_restore_status(
                backup_id="My-bucket",
                backend=b"s3",
            )
        check_error_message(self, error, storage_val_err_msg(b"s3"))

        with self.assertRaises(ValueError) as error:
            Backup(None).get_restore_status(
                backup_id="My-bucket",
                backend="s4",
            )
        check_error_message(self, error, storage_val_err_msg("s4"))

        mock_conn = mock_connection_func("get", side_effect=RequestsConnectionError)
        with self.assertRaises(RequestsConnectionError) as error:
            Backup(mock_conn).get_restore_status(
                backup_id="My-bucket",
                backend="s3",
            )
        check_error_message(self, error, connection_err_msg)

        mock_conn = mock_connection_func("get", status_code=404)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Backup(mock_conn).get_restore_status(
                backup_id="My-bucket",
                backend="s3",
            )
        check_startswith_error_message(self, error, status_code_err_msg)

        # valid calls

        mock_conn = mock_connection_func("get", status_code=200, return_json={"status": "TEST"})
        result = Backup(mock_conn).get_restore_status(
            backup_id="My-Bucket",
            backend="s3",
        )
        self.assertDictEqual(result, {"status": "TEST"})
        mock_conn.get.assert_called_with(
            path="/backups/s3/my-bucket/restore",
        )

        mock_conn = mock_connection_func(
            "get", status_code=200, return_json={"status": "TEST", "error": None}
        )
        result = Backup(mock_conn).get_restore_status(
            backup_id="My-Bucket",
            backend="gcs",
        )
        self.assertDictEqual(result, {"status": "TEST", "error": None})
        mock_conn.get.assert_called_with(
            path="/backups/gcs/my-bucket/restore",
        )

        mock_conn = mock_connection_func("get", status_code=200, return_json={"status": "TEST2"})
        result = Backup(mock_conn).get_restore_status(
            backup_id="My-Bucket123",
            backend="filesystem",
        )
        self.assertDictEqual(result, {"status": "TEST2"})
        mock_conn.get.assert_called_with(
            path="/backups/filesystem/my-bucket123/restore",
        )

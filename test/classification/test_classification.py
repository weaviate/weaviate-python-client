import unittest
from unittest.mock import patch, Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.classification.classification import Classification, ConfigBuilder
from weaviate.exceptions import UnexpectedStatusCodeException


class TestClassification(unittest.TestCase):
    def test_schedule(self):
        """
        Test the `schedule` method.
        """

        self.assertIsInstance(Classification(None).schedule(), ConfigBuilder)

    def test_get(self):
        """
        Test the `get` method.
        """

        # error messages
        uuid_type_error = lambda dt: f"'uuid' must be of type str or uuid.UUID, but was: {dt}"
        value_error = "Not valid 'uuid' or 'uuid' can not be extracted from value"
        requests_error_message = "Classification status could not be retrieved."
        unexpected_error_message = "Get classification status"

        # invalid calls
        with self.assertRaises(TypeError) as error:
            Classification(None).get(123)
        check_error_message(self, error, uuid_type_error(int))

        with self.assertRaises(ValueError) as error:
            Classification(None).get("123")
        check_error_message(self, error, value_error)

        mock_conn = mock_connection_func("get", side_effect=RequestsConnectionError("Test!"))
        with self.assertRaises(RequestsConnectionError) as error:
            Classification(mock_conn).get("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        check_error_message(self, error, requests_error_message)

        mock_conn = mock_connection_func("get", status_code=404)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            Classification(mock_conn).get("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        check_startswith_error_message(self, error, unexpected_error_message)

        # valid calls
        mock_conn = mock_connection_func("get", return_json={"OK": "GOOD"}, status_code=200)
        result = Classification(mock_conn).get("d087b7c6-a115-5c89-8cb2-f25bdeb9bf92")
        self.assertEqual(result, {"OK": "GOOD"})

    @patch("weaviate.classification.classification.Classification._check_status")
    def test_is_complete(self, mock_check_status):
        """
        Test the `is_complete` method.
        """

        mock_check_status.return_value = "OK!"
        result = Classification(None).is_complete("Test!")
        self.assertEqual(result, "OK!")
        mock_check_status.assert_called_with("Test!", "completed")

    @patch("weaviate.classification.classification.Classification._check_status")
    def test_is_failed(self, mock_check_status):
        """
        Test the `is_failed` method.
        """

        mock_check_status.return_value = "OK!"
        result = Classification(None).is_failed("Test!")
        self.assertEqual(result, "OK!")
        mock_check_status.assert_called_with("Test!", "failed")

    @patch("weaviate.classification.classification.Classification._check_status")
    def test_is_running(self, mock_check_status):
        """
        Test the `is_running` method.
        """

        mock_check_status.return_value = "OK!"
        result = Classification(None).is_running("Test!")
        self.assertEqual(result, "OK!")
        mock_check_status.assert_called_with("Test!", "running")

    @patch("weaviate.classification.classification.Classification.get")
    def test__check_status(self, mock_get):
        """
        Test the `_check_status` method.
        """

        mock_get.return_value = {"status": "failed"}

        result = Classification(None)._check_status("uuid", "running")
        self.assertFalse(result)

        result = Classification(None)._check_status("uuid", "failed")
        self.assertTrue(result)

        mock_get.side_effect = RequestsConnectionError("Test!")
        result = Classification(None)._check_status("uuid", "running")
        self.assertFalse(result)


class TestConfigBuilder(unittest.TestCase):
    def test_with_type(self):
        """
        Test the `with_type` method.
        """

        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_type("test_type")

        self.assertEqual(config._config, {"type": "test_type"})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_k(self):
        """
        Test the `with_k` method.
        """

        # without `with_settings` called
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_k(4)

        self.assertEqual(config._config, {"settings": {"k": 4}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

        # with `with_settings` called
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_k(5).with_settings({"test": "OK!"})

        self.assertEqual(config._config, {"settings": {"k": 5, "test": "OK!"}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_class_name(self):
        """
        Test the `with_class_name` method.
        """

        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        # Correct class name format (capitalized)
        result = config.with_class_name("TestClass")

        self.assertEqual(config._config, {"class": "TestClass"})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

        # Incorrect class name format (capitalized), should be capitalized by the client
        result = config.with_class_name("testClass")

        self.assertEqual(config._config, {"class": "TestClass"})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_classify_properties(self):
        """
        Test the `with_classify_properties` method.
        """

        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_classify_properties(["test1", "test2"])

        self.assertEqual(config._config, {"classifyProperties": ["test1", "test2"]})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_based_on_properties(self):
        """
        Test the `with_based_on_properties` method.
        """

        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_based_on_properties(["test1", "test2"])

        self.assertEqual(config._config, {"basedOnProperties": ["test1", "test2"]})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_source_where_filter(self):
        """
        Test the `with_source_where_filter` method.
        """

        # without other filters set before
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_source_where_filter({"test": "OK!"})

        self.assertEqual(config._config, {"filters": {"sourceWhere": {"test": "OK!"}}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

        # with other filters set before
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_training_set_where_filter({"test": "OK!"}).with_source_where_filter(
            {"test": "OK!"}
        )

        self.assertEqual(
            config._config,
            {"filters": {"sourceWhere": {"test": "OK!"}, "trainingSetWhere": {"test": "OK!"}}},
        )
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_training_set_where_filter(self):
        """
        Test the `with_training_set_where_filter` method.
        """

        # without other filters set before
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_training_set_where_filter({"test": "OK!"})

        self.assertEqual(config._config, {"filters": {"trainingSetWhere": {"test": "OK!"}}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

        # with other filters set before
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_target_where_filter({"test": "OK!"}).with_training_set_where_filter(
            {"test": "OK!"}
        )

        self.assertEqual(
            config._config,
            {"filters": {"trainingSetWhere": {"test": "OK!"}, "targetWhere": {"test": "OK!"}}},
        )
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_target_where_filter(self):
        """
        Test the `with_target_where_filter` method.
        """

        # without other filters set before
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_target_where_filter({"test": "OK!"})

        self.assertEqual(config._config, {"filters": {"targetWhere": {"test": "OK!"}}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

        # with other filters set before
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_source_where_filter({"test": "OK!"}).with_target_where_filter(
            {"test": "OK!"}
        )

        self.assertEqual(
            config._config,
            {"filters": {"targetWhere": {"test": "OK!"}, "sourceWhere": {"test": "OK!"}}},
        )
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_wait_for_completion(self):
        """
        Test the `with_wait_for_completion` method.
        """

        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_wait_for_completion()

        self.assertEqual(config._config, {})
        self.assertTrue(config._wait_for_completion)
        self.assertIs(result, config)

    def test_with_settings(self):
        """
        Test the `with_settings` method.
        """

        # without `with_k` called
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_settings({"test": "OK!"})

        self.assertEqual(config._config, {"settings": {"test": "OK!"}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

        # with `with_k` called
        config = ConfigBuilder(None, None)
        self.assertEqual(config._config, {})
        self.assertFalse(config._wait_for_completion)

        result = config.with_settings({"test": "OK!"}).with_k(7)

        self.assertEqual(config._config, {"settings": {"k": 7, "test": "OK!"}})
        self.assertFalse(config._wait_for_completion)
        self.assertIs(result, config)

    def test__validate_config(self):
        """
        Test the `_validate_config` method.
        """

        # error messages
        field_error_message = lambda f: f"{f} is not set for this classification"
        settings_error_message = '"settings" should be of type dict'
        k_error_message = "k is not set for this classification"

        # test required fields without "classifyProperties"
        config = (
            ConfigBuilder(None, None)
            .with_type("Test!")
            .with_class_name("Test!")
            .with_based_on_properties(["Test!"])
        )
        with self.assertRaises(ValueError) as error:
            config._validate_config()
        check_error_message(self, error, field_error_message("classifyProperties"))

        # test required fields without "basedOnProperties"
        config = (
            ConfigBuilder(None, None)
            .with_type("Test!")
            .with_class_name("Test!")
            .with_classify_properties(["Test!"])
        )
        with self.assertRaises(ValueError) as error:
            config._validate_config()
        check_error_message(self, error, field_error_message("basedOnProperties"))

        # test required fields without "class"
        config = (
            ConfigBuilder(None, None)
            .with_type("Test!")
            .with_based_on_properties(["Test!"])
            .with_classify_properties(["Test!"])
        )
        with self.assertRaises(ValueError) as error:
            config._validate_config()
        check_error_message(self, error, field_error_message("class"))

        # test required fields without "type"
        config = (
            ConfigBuilder(None, None)
            .with_based_on_properties(["Test!"])
            .with_class_name("Test!")
            .with_classify_properties(["Test!"])
        )
        with self.assertRaises(ValueError) as error:
            config._validate_config()
        check_error_message(self, error, field_error_message("type"))

        # test required fields with all required
        config = (
            ConfigBuilder(None, None)
            .with_based_on_properties(["Test!"])
            .with_type("Test!")
            .with_class_name("Test!")
            .with_classify_properties(["Test!"])
        )
        config._validate_config()

        # test settings
        config = (
            ConfigBuilder(None, None)
            .with_based_on_properties(["Test!"])
            .with_type("Test!")
            .with_class_name("Test!")
            .with_classify_properties(["Test!"])
            .with_settings(["Test!"])
        )
        with self.assertRaises(TypeError) as error:
            config._validate_config()
        check_error_message(self, error, settings_error_message)

        # test knn without k
        config = (
            ConfigBuilder(None, None)
            .with_based_on_properties(["Test!"])
            .with_type("knn")
            .with_class_name("Test!")
            .with_classify_properties(["Test!"])
        )
        with self.assertRaises(ValueError) as error:
            config._validate_config()
        check_error_message(self, error, k_error_message)

        # test knn with k
        config = (
            ConfigBuilder(None, None)
            .with_based_on_properties(["Test!"])
            .with_type("knn")
            .with_class_name("Test!")
            .with_classify_properties(["Test!"])
            .with_k(4)
        )
        config._validate_config()

    def test__start(self):
        """
        Test the `_start` method.
        """

        # error messages
        requests_error_message = "Classification may not started."
        unexpected_error_message = "Start classification"

        # invalid calls
        mock_conn = mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        config = ConfigBuilder(mock_conn, None)
        with self.assertRaises(RequestsConnectionError) as error:
            config._start()
        check_error_message(self, error, requests_error_message)
        mock_conn.post.assert_called_with(path="/classifications", weaviate_object={})

        mock_conn = mock_connection_func("post", status_code=200)
        config = ConfigBuilder(mock_conn, None).with_class_name("Test!")
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            config._start()
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_conn.post.assert_called_with(
            path="/classifications", weaviate_object={"class": "Test!"}
        )

        # valid calls
        mock_conn = mock_connection_func("post", status_code=201, return_json="OK!")
        config = ConfigBuilder(mock_conn, None).with_class_name("TestClass").with_type("TestType")
        self.assertEqual(config._start(), "OK!")
        mock_conn.post.assert_called_with(
            path="/classifications", weaviate_object={"class": "TestClass", "type": "TestType"}
        )

    @patch("weaviate.classification.config_builder.ConfigBuilder._start")
    @patch(
        "weaviate.classification.config_builder.ConfigBuilder._validate_config", return_value=None
    )
    def test_do(self, mock_validate_config, mock_start):
        """
        Test the `do` method.
        """

        mock_start.return_value = {"status": "test"}
        config = ConfigBuilder(None, None)
        self.assertEqual(config.do(), {"status": "test"})

        mock_start.return_value = {"status": "test", "id": "test_id"}
        mock_classification = Mock()  # mock self._classification instance

        def mock_waiting(test):
            if mock_waiting.called:
                return False
            mock_waiting.called = True
            return True

        mock_waiting.called = False  # initialize static variable
        mock_classification.is_running.side_effect = mock_waiting
        mock_classification.get.return_value = "test"
        config = ConfigBuilder(None, mock_classification).with_wait_for_completion()
        self.assertEqual(config.do(), "test")

    def test_integration_config(self):
        """
        Test all `with_` methods together that change the configuration.
        """

        config = (
            ConfigBuilder(None, None)
            .with_type("test_type")
            .with_k(4)
            .with_class_name("TestClass")
            .with_classify_properties(["Test1!"])
            .with_based_on_properties(["Test2!"])
            .with_source_where_filter({"test": "OK1!"})
            .with_training_set_where_filter({"test": "OK2!"})
            .with_target_where_filter({"test": "OK3!"})
            .with_settings({"additional": "test_settings"})
        )
        expected_config = {
            "type": "test_type",
            "settings": {"k": 4, "additional": "test_settings"},
            "class": "TestClass",
            "classifyProperties": ["Test1!"],
            "basedOnProperties": ["Test2!"],
            "filters": {
                "sourceWhere": {"test": "OK1!"},
                "trainingSetWhere": {"test": "OK2!"},
                "targetWhere": {"test": "OK3!"},
            },
        }
        self.assertEqual(config._config, expected_config)

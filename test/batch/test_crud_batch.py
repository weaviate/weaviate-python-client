import unittest
from numbers import Real
from unittest.mock import Mock, patch

import pytest
from requests import ReadTimeout
from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.batch import Batch
from weaviate.batch.crud_batch import WeaviateErrorRetryConf
from weaviate.batch.requests import ObjectsBatchRequest, ReferenceBatchRequest
from weaviate.data.replication import ConsistencyLevel
from weaviate.exceptions import UnexpectedStatusCodeException


@pytest.mark.parametrize(
    "num,excl,incl",
    [
        (3, ["some entry"], ["other entry"]),
        (-1, None, None),
        (1, ["some entry", 1], None),
        (1, None, ["some entry", 1]),
        (1, None, []),
    ],
)
def test_retry_config_both_lists(num, excl, incl):
    """Test that either include or exclude list can be given."""
    with pytest.raises(ValueError):
        WeaviateErrorRetryConf(number_retries=num, errors_to_exclude=excl, errors_to_include=incl)


class TestBatch(unittest.TestCase):
    def check_instance(
        self,
        batch: Batch,
        recom_num_obj: int = None,
        recom_num_ref: int = None,
        batch_size: int = None,
        creation_time: Real = 2,  # this is based on the default timeout_config of the Client class
        timeout_retries: int = 3,
        connection_error_retries: int = 3,
        batching_type: str = None,
        num_workers: int = 1,
        consistency_level: ConsistencyLevel = None,
    ) -> None:
        """
        Check all configurable attributes of the Batch instance.
        """

        self.assertEqual(batch._recommended_num_objects, recom_num_obj)
        self.assertEqual(batch._recommended_num_references, recom_num_ref)
        self.assertEqual(batch._batch_size, batch_size)
        self.assertEqual(batch._creation_time, creation_time)
        self.assertEqual(batch._timeout_retries, timeout_retries)
        self.assertEqual(batch._connection_error_retries, connection_error_retries)
        self.assertEqual(batch._batching_type, batching_type)
        self.assertEqual(batch._num_workers, num_workers)
        self.assertEqual(batch._consistency_level, consistency_level)

    # TEST SETTERS/GETTERS

    def test_timeout_retries(self):
        """
        Test Setter and Getter for 'timeout_retries'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch=batch)

        self.assertEqual(batch.timeout_retries, 3)
        self.check_instance(batch, timeout_retries=3)

        batch.timeout_retries = 10
        self.assertEqual(batch.timeout_retries, 10)
        self.check_instance(batch, timeout_retries=10)

        batch.timeout_retries = 0
        self.assertEqual(batch.timeout_retries, 0)
        self.check_instance(batch, timeout_retries=0)

        batch.timeout_retries = 1
        self.assertEqual(batch.timeout_retries, 1)
        self.check_instance(batch, timeout_retries=1)

        # exceptions
        ## error messages
        value_error = "'timeout_retries' must be positive, i.e. greater or equal that zero (>=0)."
        type_error = f"'timeout_retries' must be of type {int}."

        #######################################################################
        # test wrong value
        with self.assertRaises(ValueError) as error:
            batch.timeout_retries = -1
        self.assertEqual(batch.timeout_retries, 1)
        self.check_instance(batch, timeout_retries=1)
        check_error_message(self, error, value_error)

        #######################################################################
        # test wrong type
        with self.assertRaises(TypeError) as error:
            batch.timeout_retries = True
        self.assertEqual(batch.timeout_retries, 1)
        self.check_instance(batch, timeout_retries=1)
        check_error_message(self, error, type_error)

        with self.assertRaises(TypeError) as error:
            batch.timeout_retries = "2"
        self.assertEqual(batch.timeout_retries, 1)
        self.check_instance(batch, timeout_retries=1)
        check_error_message(self, error, type_error)

    def test_connection_error_retries(self):
        """
        Test Setter and Getter for 'connection_error_retries'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch=batch)

        self.assertEqual(batch.connection_error_retries, 3)
        self.check_instance(batch, connection_error_retries=3)

        batch.connection_error_retries = 10
        self.assertEqual(batch.connection_error_retries, 10)
        self.check_instance(batch, connection_error_retries=10)

        batch.connection_error_retries = 0
        self.assertEqual(batch.connection_error_retries, 0)
        self.check_instance(batch, connection_error_retries=0)

        batch.connection_error_retries = 1
        self.assertEqual(batch.connection_error_retries, 1)
        self.check_instance(batch, connection_error_retries=1)

        # exceptions
        ## error messages
        value_error = (
            "'connection_error_retries' must be positive, i.e. greater or equal that zero (>=0)."
        )
        type_error = f"'connection_error_retries' must be of type {int}."

        #######################################################################
        # test wrong value
        with self.assertRaises(ValueError) as error:
            batch.connection_error_retries = -1
        self.assertEqual(batch.connection_error_retries, 1)
        self.check_instance(batch, connection_error_retries=1)
        check_error_message(self, error, value_error)

        #######################################################################
        # test wrong type
        with self.assertRaises(TypeError) as error:
            batch.connection_error_retries = True
        self.assertEqual(batch.connection_error_retries, 1)
        self.check_instance(batch, connection_error_retries=1)
        check_error_message(self, error, type_error)

        with self.assertRaises(TypeError) as error:
            batch.connection_error_retries = "2"
        self.assertEqual(batch.connection_error_retries, 1)
        self.check_instance(batch, connection_error_retries=1)
        check_error_message(self, error, type_error)

    def test_recommended_num_objects(self):
        """
        Test Setter and Getter for 'recommended_num_objects'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch)

        self.assertIsNone(batch.recommended_num_objects)
        self.check_instance(batch)

        batch._recommended_num_objects = 10
        self.assertEqual(batch.recommended_num_objects, 10)
        self.check_instance(batch, recom_num_obj=10)

        batch._recommended_num_objects = 20
        self.assertEqual(batch.recommended_num_objects, 20)
        self.check_instance(batch, recom_num_obj=20)

    def test_recommended_num_references(self):
        """
        Test Setter and Getter for 'recommended_num_references'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch)

        self.assertIsNone(batch.recommended_num_references)
        self.check_instance(batch)

        batch._recommended_num_references = 10
        self.assertEqual(batch.recommended_num_references, 10)
        self.check_instance(batch, recom_num_ref=10)

        batch._recommended_num_references = 20
        self.assertEqual(batch.recommended_num_references, 20)
        self.check_instance(batch, recom_num_ref=20)

    @patch("weaviate.batch.crud_batch.Batch._auto_create")
    def test_batch_size(self, mock_auto_create):
        """
        Test Setter and Getter for 'batch_size'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch)

        self.assertIsNone(batch.batch_size)
        self.check_instance(batch)

        #######################################################################
        # test batch_size: None -> int
        batch.batch_size = 10
        self.assertEqual(batch.batch_size, 10)
        self.check_instance(
            batch, batch_size=10, batching_type="fixed", recom_num_obj=10, recom_num_ref=10
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # test batch_size: int -> int and dynamic enabled, one recommended set to None
        ## set some attributes manually (ONLY WHEN TESTING!!!)
        batch._batching_type = "dynamic"
        batch._recommended_num_objects = None

        batch.batch_size = 200
        self.assertEqual(batch.batch_size, 200)
        self.check_instance(
            batch, batch_size=200, batching_type="dynamic", recom_num_obj=200, recom_num_ref=10
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # test batch_size: int -> None
        batch.batch_size = None
        self.assertIsNone(batch.batch_size)
        self.check_instance(
            batch, batch_size=None, batching_type=None, recom_num_obj=200, recom_num_ref=10
        )
        mock_auto_create.assert_not_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # test exceptions
        ## messages
        type_error = f"'batch_size' must be of type {int}."
        value_error = "'batch_size' must be positive, i.e. greater that zero (>0)."

        with self.assertRaises(TypeError) as error:
            batch.batch_size = False
        check_error_message(self, error, type_error)
        self.check_instance(
            batch, batch_size=None, batching_type=None, recom_num_obj=200, recom_num_ref=10
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(TypeError) as error:
            batch.batch_size = 100.5
        check_error_message(self, error, type_error)
        self.check_instance(
            batch, batch_size=None, batching_type=None, recom_num_obj=200, recom_num_ref=10
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.batch_size = 0
        check_error_message(self, error, value_error)
        self.check_instance(
            batch, batch_size=None, batching_type=None, recom_num_obj=200, recom_num_ref=10
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.batch_size = -100
        check_error_message(self, error, value_error)
        self.check_instance(
            batch, batch_size=None, batching_type=None, recom_num_obj=200, recom_num_ref=10
        )
        mock_auto_create.assert_not_called()

    @patch("weaviate.batch.crud_batch.Batch._auto_create")
    def test_dynamic(self, mock_auto_create):
        """
        Test Setter and Getter for 'dynamic'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch)

        self.assertFalse(batch.dynamic)
        self.check_instance(batch)

        #######################################################################
        # test when batching_type is None (setter does nothing)
        batch.dynamic = True
        self.assertFalse(batch.dynamic)
        self.check_instance(batch, batching_type=None)

        #######################################################################
        # test when batching_type not None
        batch._batching_type = "fixed"
        batch.dynamic = True
        self.assertTrue(batch.dynamic)
        self.check_instance(batch, batching_type="dynamic")
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        # set again to True
        batch.dynamic = True
        self.assertTrue(batch.dynamic)
        self.check_instance(batch, batching_type="dynamic")
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        batch.dynamic = False
        self.assertFalse(batch.dynamic)
        self.check_instance(batch, batching_type="fixed")
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # test exceptions
        ## messages
        type_error = "'dynamic' must be of type bool."

        with self.assertRaises(TypeError) as error:
            batch.dynamic = 0
        check_error_message(self, error, type_error)
        self.check_instance(batch, batching_type="fixed")
        mock_auto_create.assert_not_called()

    @patch("weaviate.batch.crud_batch.Batch._auto_create")
    def test_creation_time(self, mock_auto_create):
        """
        Test Setter and Getter for 'creation_time'.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch)

        self.assertEqual(batch.creation_time, 2)
        self.check_instance(batch)

        #######################################################################
        # test when batching_type and recommended are None
        batch.creation_time = 5.0
        self.assertEqual(batch.creation_time, 5.0)
        self.check_instance(batch, creation_time=5.0)
        mock_auto_create.assert_not_called()

        #######################################################################
        # test when recommended are not None, but batching_type is None
        batch._recommended_num_objects = 100
        batch._recommended_num_references = 200
        batch.creation_time = 20.0
        self.assertEqual(batch.creation_time, 20.0)
        self.check_instance(
            batch,
            creation_time=20.0,
            batching_type=None,
            recom_num_obj=400,
            recom_num_ref=800,
        )
        mock_auto_create.assert_not_called()

        #######################################################################
        # test when recommended are None
        batch.batch_size = 10  # sets batching_type to 'fixed'
        batch.creation_time = 5.0
        self.assertEqual(batch.creation_time, 5.0)
        self.check_instance(
            batch,
            batch_size=10,
            creation_time=5.0,
            batching_type="fixed",
            recom_num_obj=100,
            recom_num_ref=200,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # test exceptions
        ## messages
        type_error = f"'creation_time' must be of type {Real}."
        value_error = "'creation_time' must be positive, i.e. greater that zero (>0)."

        with self.assertRaises(TypeError) as error:
            batch.creation_time = True
        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=10,
            creation_time=5.0,
            batching_type="fixed",
            recom_num_obj=100,
            recom_num_ref=200,
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(TypeError) as error:
            batch.creation_time = "10.6"
        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=10,
            creation_time=5.0,
            batching_type="fixed",
            recom_num_obj=100,
            recom_num_ref=200,
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.creation_time = 0.0
        check_error_message(self, error, value_error)
        self.check_instance(
            batch,
            batch_size=10,
            creation_time=5.0,
            batching_type="fixed",
            recom_num_obj=100,
            recom_num_ref=200,
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.creation_time = -10.0
        check_error_message(self, error, value_error)
        self.check_instance(
            batch,
            batch_size=10,
            creation_time=5.0,
            batching_type="fixed",
            recom_num_obj=100,
            recom_num_ref=200,
        )
        mock_auto_create.assert_not_called()

    def test_shape_and_num_data(self):
        """
        Test the `shape`, `num_objects` and `num_references` property/methods.
        """

        batch = Batch(mock_connection_func(server_version="1.14.0"))

        self.assertEqual(batch.num_objects(), 0)
        self.assertEqual(batch.num_references(), 0)
        self.assertEqual(batch.shape, (0, 0))

        #######################################################################
        # add one object
        batch.add_data_object({}, "Test")

        self.assertEqual(batch.num_objects(), 1)
        self.assertEqual(batch.num_references(), 0)
        self.assertEqual(batch.shape, (1, 0))

        #######################################################################
        # add one object
        batch.add_data_object({}, "Test")

        self.assertEqual(batch.num_objects(), 2)
        self.assertEqual(batch.num_references(), 0)
        self.assertEqual(batch.shape, (2, 0))

        #######################################################################
        # add one reference
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37394",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37395",
        )

        self.assertEqual(batch.num_objects(), 2)
        self.assertEqual(batch.num_references(), 1)
        self.assertEqual(batch.shape, (2, 1))

        #######################################################################
        # add one reference
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37396",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37397",
        )

        self.assertEqual(batch.num_objects(), 2)
        self.assertEqual(batch.num_references(), 2)
        self.assertEqual(batch.shape, (2, 2))

    @patch("weaviate.batch.crud_batch.Batch.shutdown")
    @patch("weaviate.batch.crud_batch.Batch.start")
    @patch("weaviate.batch.crud_batch.Batch.flush")
    def test_enter_exit(self, mock_flush, mock_start, mock_shutdown):
        """
        Test `__enter__` and `__exit__` methods.
        """

        mock_start.return_value = "test"
        batch = Batch(mock_connection_func())

        with batch as b:
            self.assertEqual("test", b)
            mock_flush.assert_not_called()
            mock_shutdown.assert_not_called()
            mock_start.assert_called()
            mock_start.reset_mock()
        mock_flush.assert_called()
        mock_shutdown.assert_called()
        mock_start.assert_not_called()

    def test_shutdown(
        self,
    ):
        """
        Test `shutdown` method.
        """

        # initial value for executor (None)
        batch = Batch(mock_connection_func())
        with patch("weaviate.batch.crud_batch.BatchExecutor") as mock_executor:
            mock_executor.shutdown.assert_not_called()
            batch.shutdown()
            mock_executor.shutdown.assert_not_called()

        # shutdown executor
        batch = Batch(mock_connection_func())
        mock_executor = Mock()
        mock_executor.is_shutdown.return_value = True
        batch._executor = mock_executor
        mock_executor.shutdown.assert_not_called()
        mock_executor.is_shutdown.assert_not_called()
        batch.shutdown()
        mock_executor.is_shutdown.assert_called()
        mock_executor.shutdown.assert_not_called()

        # running executor
        batch = Batch(mock_connection_func())
        mock_executor = Mock()
        mock_executor.is_shutdown.return_value = False
        batch._executor = mock_executor
        mock_executor.shutdown.assert_not_called()
        mock_executor.is_shutdown.assert_not_called()
        batch.shutdown()
        mock_executor.is_shutdown.assert_called()
        mock_executor.shutdown.assert_called()

    @patch("weaviate.batch.crud_batch.BatchExecutor")
    def test_start(self, mock_executor_class):
        """
        Test `start` method.
        """

        executor = Mock()
        executor.is_shutdown.return_value = False
        mock_executor_class.return_value = executor

        batch = Batch(mock_connection_func())
        mock_executor_class.assert_not_called()

        mock_executor_class.reset_mock()
        mock_executor_class.return_value = executor
        executor.is_shutdown.assert_not_called()
        result = batch.start()
        self.assertEqual(result, batch)
        executor.is_shutdown.assert_not_called()
        mock_executor_class.assert_called()

        executor.reset_mock()

        mock_executor_class.reset_mock()
        mock_executor_class.return_value = executor
        executor.is_shutdown.assert_not_called()
        result = batch.start()
        self.assertEqual(result, batch)
        executor.is_shutdown.assert_called()
        mock_executor_class.assert_not_called()

        executor.reset_mock()

        executor.is_shutdown.return_value = True
        batch._num_workers = 2
        result = batch.start()
        self.assertEqual(result, batch)
        executor.is_shutdown.assert_called()
        mock_executor_class.assert_called_with(max_workers=2)

    @patch("weaviate.batch.crud_batch.Batch._send_batch_requests")
    def test_flush(self, mock_send_batch_requests):
        """
        Test `flush` method.
        """

        batch = Batch(mock_connection_func())

        batch.flush()
        mock_send_batch_requests.assert_called_with(force_wait=True)
        mock_send_batch_requests.reset_mock()

    @patch("weaviate.batch.crud_batch.Batch._send_batch_requests")
    def test_auto_create(self, mock_send_batch_requests):
        """
        Test `_auto_create` method through `add_*` methods.
        """

        batch = Batch(mock_connection_func(server_version="1.14.0"))
        batch.batch_size = 2  # this enables auto_create with batching `fixed`

        #######################################################################
        # only objects and batching_type 'fixed'
        batch.add_data_object({}, "Test")
        mock_send_batch_requests.assert_not_called()
        batch.add_data_object({}, "Test")
        mock_send_batch_requests.assert_called()
        mock_send_batch_requests.reset_mock()

        #######################################################################
        # add references too, batching_type 'fixed'
        batch.batch_size = 4
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37393",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37394",
        )
        mock_send_batch_requests.assert_not_called()
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37396",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37397",
        )
        mock_send_batch_requests.assert_called()
        mock_send_batch_requests.reset_mock()

        #######################################################################
        # batching_type 'dynamic'
        batch = Batch(mock_connection_func(server_version="1.14.0"))
        batch.batch_size = 2  # this enables auto_create with batching `fixed`
        batch.dynamic = True  # NOTE: recommended are set to 2 when we set the batch_size to 2
        batch.add_data_object({}, "Test")
        mock_send_batch_requests.assert_not_called()
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37393",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37394",
        )
        mock_send_batch_requests.assert_not_called()
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37396",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37397",
        )
        mock_send_batch_requests.assert_called()
        batch.add_data_object({}, "Test")
        mock_send_batch_requests.assert_called()
        mock_send_batch_requests.reset_mock()

        #######################################################################
        # exceptions
        ## error messages
        value_error = f'Unsupported batching type "{None}"'
        batch = Batch(mock_connection_func())
        with self.assertRaises(ValueError) as error:
            batch._auto_create()  # This should not be called like this, only for test purposes
        check_error_message(self, error, value_error)

    @patch("weaviate.batch.crud_batch.Batch._auto_create")
    def test_add_data_object(self, mock_auto_create):
        """
        Test `add_data_object` method.
        """

        batch = Batch(mock_connection_func())
        batch._objects_batch = Mock()  # to test if the add method is called

        batch.add_data_object({}, "Test")
        self.assertEqual(batch._objects_batch.add.call_count, 1)
        batch._objects_batch.add.assert_called_with(
            class_name="Test",
            data_object={},
            uuid=None,
            vector=None,
        )
        mock_auto_create.assert_not_called()

        batch.add_data_object({}, "Test")
        self.assertEqual(batch._objects_batch.add.call_count, 2)
        batch._objects_batch.add.assert_called_with(
            class_name="Test",
            data_object={},
            uuid=None,
            vector=None,
        )
        mock_auto_create.assert_not_called()

        batch._batching_type = (
            "fixed"  # This should not be called like this, only for test purposes
        )
        batch.add_data_object({}, "Test")
        self.assertEqual(batch._objects_batch.add.call_count, 3)
        batch._objects_batch.add.assert_called_with(
            class_name="Test",
            data_object={},
            uuid=None,
            vector=None,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        batch._batching_type = (
            "dynamic"  # This should not be called like this, only for test purposes
        )
        batch.add_data_object({}, "Test")
        self.assertEqual(batch._objects_batch.add.call_count, 4)
        batch._objects_batch.add.assert_called_with(
            class_name="Test",
            data_object={},
            uuid=None,
            vector=None,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        batch.add_data_object({}, "test")
        self.assertEqual(batch._objects_batch.add.call_count, 5)
        batch._objects_batch.add.assert_called_with(
            class_name="Test",
            data_object={},
            uuid=None,
            vector=None,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

    @patch("weaviate.batch.crud_batch.Batch._auto_create")
    def test_add_reference(self, mock_auto_create):
        """
        Test `add_reference` method.
        """

        batch = Batch(mock_connection_func(server_version="1.14.0"))
        batch._reference_batch = Mock()  # to test if the add method is called

        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37391",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37392",
        )
        self.assertEqual(batch._reference_batch.add.call_count, 1)
        batch._reference_batch.add.assert_called_with(
            from_object_class_name="Test",
            from_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37391",
            from_property_name="test",
            to_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37392",
            to_object_class_name=None,
        )
        mock_auto_create.assert_not_called()

        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37393",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37394",
        )
        self.assertEqual(batch._reference_batch.add.call_count, 2)
        batch._reference_batch.add.assert_called_with(
            from_object_class_name="Test",
            from_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37393",
            from_property_name="test",
            to_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37394",
            to_object_class_name=None,
        )
        mock_auto_create.assert_not_called()

        batch._batching_type = (
            "fixed"  # This should never be called like this, we do it for test purposes
        )
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37396",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37397",
        )
        self.assertEqual(batch._reference_batch.add.call_count, 3)
        batch._reference_batch.add.assert_called_with(
            from_object_class_name="Test",
            from_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37396",
            from_property_name="test",
            to_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37397",
            to_object_class_name=None,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        batch._batching_type = (
            "dynamic"  # This should never be called like this, we do it for test purposes
        )
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37390",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37399",
        )
        self.assertEqual(batch._reference_batch.add.call_count, 4)
        batch._reference_batch.add.assert_called_with(
            from_object_class_name="Test",
            from_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37390",
            from_property_name="test",
            to_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37399",
            to_object_class_name=None,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37395",
            "test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37319",
        )
        self.assertEqual(batch._reference_batch.add.call_count, 5)
        batch._reference_batch.add.assert_called_with(
            from_object_class_name="Test",
            from_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37395",
            from_property_name="test",
            to_object_uuid="f0153f24-3923-4046-919b-6a3e8fd37319",
            to_object_class_name=None,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

    @patch("weaviate.batch.crud_batch.Batch._create_data")
    def test_create_objects(self, mock_create_data):
        """
        Test `create_objects` method.
        """

        batch = Batch(mock_connection_func())
        ## mock the requests.Response object
        mock_response = Mock()
        mock_response.json.return_value = "Test"
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_create_data.return_value = mock_response

        #######################################################################
        # create zero length batch
        self.assertEqual(batch.create_objects(), [])
        mock_create_data.assert_not_called()
        self.check_instance(batch)

        #######################################################################
        # add objects
        batch.add_data_object({}, "Test")
        batch.add_data_object({}, "Test")
        self.assertEqual(batch.create_objects(), "Test")
        mock_create_data.assert_called()
        self.check_instance(batch, recom_num_obj=0)
        self.assertEqual(batch.num_objects(), 0)

    @patch("weaviate.batch.crud_batch.Batch._create_data")
    def test_create_references(self, mock_create_data):
        """
        Test `create_references` method.
        """

        batch = Batch(mock_connection_func(server_version="1.14.0"))
        ## mock the requests.Response object
        mock_response = Mock()
        mock_response.json.return_value = "Test"
        mock_response.elapsed.total_seconds.return_value = 1.0
        mock_create_data.return_value = mock_response

        #######################################################################
        # create zero length batch
        self.assertEqual(batch.create_references(), [])
        mock_create_data.assert_not_called()
        self.check_instance(batch)

        #######################################################################
        # add objects
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37391",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37398",
        )
        batch.add_reference(
            "f0153f24-3923-4046-919b-6a3e8fd37390",
            "Test",
            "test",
            "f0153f24-3923-4046-919b-6a3e8fd37399",
        )
        self.assertEqual(batch.create_references(), "Test")
        mock_create_data.assert_called()
        self.check_instance(batch, recom_num_ref=0)
        self.assertEqual(batch.num_references(), 0)

    def test_create_data(self):
        """
        Test the `_create_data` method.
        """

        #######################################################################
        # test status_code == 200, timeout_retries = 0
        mock_connection = mock_connection_func("post", status_code=200)
        batch = Batch(mock_connection)
        batch._create_data("references", ReferenceBatchRequest())
        mock_connection.post.assert_called_with(
            path="/batch/references",
            weaviate_object=[],
            params=None,
        )
        self.assertEqual(mock_connection.post.call_count, 1)

        #######################################################################
        # timeout_retries = 2, and no exception raised
        mock_connection = mock_connection_func("post", status_code=200)
        batch = Batch(mock_connection)
        batch.timeout_retries = 2
        batch.consistency_level = ConsistencyLevel.QUORUM
        batch._create_data("references", ReferenceBatchRequest())
        mock_connection.post.assert_called_with(
            path="/batch/references",
            weaviate_object=[],
            params={"consistency_level": "QUORUM"},
        )
        self.assertEqual(mock_connection.post.call_count, 1)

        #######################################################################
        # test errors
        #######################################################################
        ## error messages
        requests_error_message = "Batch was not added to weaviate."
        unexpected_error_message = lambda data: f"Create {data} in batch"

        #######################################################################
        ## test RequestsConnectionError
        mock_connection = mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        batch = Batch(mock_connection)
        batch.consistency_level = ConsistencyLevel.ONE
        with self.assertRaises(RequestsConnectionError) as error:
            batch._create_data("objects", ObjectsBatchRequest())
        check_error_message(self, error, requests_error_message)
        mock_connection.post.assert_called_with(
            path="/batch/objects",
            weaviate_object={"fields": ["ALL"], "objects": []},
            params={"consistency_level": "ONE"},
        )

        ## test ConnectionError, connection_error_retries = 0
        mock_connection = mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        mock_connection.timeout_config = (2, 100)
        batch = Batch(mock_connection)
        batch.connection_error_retries = 0
        batch.consistency_level = ConsistencyLevel.ALL
        with self.assertRaises(RequestsConnectionError) as error:
            batch._create_data("references", ReferenceBatchRequest())
        check_startswith_error_message(self, error, requests_error_message)
        mock_connection.post.assert_called_with(
            path="/batch/references", weaviate_object=[], params={"consistency_level": "ALL"}
        )
        self.assertEqual(mock_connection.post.call_count, 1)

        ## test ConnectionError, connection_error_retries = 3 (default)
        mock_connection = mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        mock_connection.timeout_config = (2, 100)
        batch = Batch(mock_connection)
        with self.assertRaises(RequestsConnectionError) as error:
            batch._create_data("objects", ObjectsBatchRequest())
        check_startswith_error_message(self, error, requests_error_message)
        mock_connection.post.assert_called_with(
            path="/batch/objects",
            weaviate_object={"fields": ["ALL"], "objects": []},
            params=None,
        )
        self.assertEqual(mock_connection.post.call_count, 3 + 1)

        ## test alternating errors
        i_for_alt_errors = 0

        def alternating_errors():
            nonlocal i_for_alt_errors
            if i_for_alt_errors % 2 == 0:
                err = RequestsConnectionError
            else:
                err = ReadTimeout
            i_for_alt_errors += 1
            raise err

        ## test status_code != 200
        mock_connection = mock_connection_func("post", status_code=204)
        batch = Batch(mock_connection)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            batch._create_data("references", ReferenceBatchRequest())
        check_startswith_error_message(self, error, unexpected_error_message("references"))
        mock_connection.post.assert_called_with(
            path="/batch/references",
            weaviate_object=[],
            params=None,
        )

        batch = Batch(mock_connection)
        with self.assertRaises(ValueError) as error:
            batch.consistency_level = 1
        check_startswith_error_message(self, error, "1 is not a valid ConsistencyLevel")

    @patch("weaviate.batch.crud_batch.Batch._auto_create")
    def test_configure_call(self, mock_auto_create):
        """
        Test the `configure` method, which is the same as `__call__`.
        """

        batch = Batch(mock_connection_func())
        self.check_instance(batch)
        #
        with self.assertRaises(ValueError) as error:
            batch.configure(consistency_level=1)
        check_startswith_error_message(self, error, "1 is not a valid ConsistencyLevel")
        #######################################################################
        # batching_type: None -> 'fixed'
        return_batch = batch.configure(
            batch_size=100,
            creation_time=20.76,
            timeout_retries=2,
            consistency_level=ConsistencyLevel.ALL,
        )
        self.assertEqual(batch, return_batch)
        self.check_instance(
            batch,
            batch_size=100,
            creation_time=20.76,
            timeout_retries=2,
            batching_type="fixed",
            consistency_level="ALL",
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # batching_type: 'fixed' -> 'dynamic'
        return_batch = batch.configure(
            batch_size=200,
            creation_time=2.5,
            timeout_retries=0,
            dynamic=True,
        )
        self.assertEqual(batch, return_batch)
        self.check_instance(
            batch,
            batch_size=200,
            creation_time=2.5,
            timeout_retries=0,
            batching_type="dynamic",
            recom_num_obj=200,
            recom_num_ref=200,
        )
        mock_auto_create.assert_called()
        mock_auto_create.reset_mock()

        #######################################################################
        # batching_type: 'dynamic' -> None
        return_batch = batch.configure(
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            dynamic=True,
            consistency_level="QUORUM",
        )
        self.assertEqual(batch, return_batch)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
            consistency_level=ConsistencyLevel.QUORUM,
        )
        mock_auto_create.assert_not_called()

        #######################################################################
        # test errors
        #######################################################################

        #######################################################################
        # creation_time

        type_error = f"'creation_time' must be of type {Real}."
        value_error = "'creation_time' must be positive, i.e. greater that zero (>0)."

        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=None,
                creation_time=True,
                timeout_retries=10,
                dynamic=True,
            )

        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=None,
                creation_time="12.5",
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.configure(
                batch_size=None,
                creation_time=0.0,
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, value_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.configure(
                batch_size=None,
                creation_time=-1,
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, value_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        #######################################################################
        # timeout_retries
        value_error = "'timeout_retries' must be positive, i.e. greater or equal that zero (>=0)."
        type_error = f"'timeout_retries' must be of type {int}."

        #######################################################################
        ## test wrong value
        with self.assertRaises(ValueError) as error:
            batch.configure(
                batch_size=None,
                creation_time=12.5,
                timeout_retries=-1,
                dynamic=True,
            )
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        check_error_message(self, error, value_error)

        #######################################################################
        ## test wrong type
        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=None,
                creation_time=12.5,
                timeout_retries=True,
                dynamic=True,
            )
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        check_error_message(self, error, type_error)

        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=None,
                creation_time=12.5,
                timeout_retries="12",
                dynamic=True,
            )
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        check_error_message(self, error, type_error)

        #######################################################################
        # dynamic
        type_error = "'dynamic' must be of type bool."

        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=100,
                creation_time=12.5,
                timeout_retries=10,
                dynamic=0,
            )
        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        #######################################################################
        # dynamic
        type_error = f"'batch_size' must be of type {int}."
        value_error = "'batch_size' must be positive, i.e. greater that zero (>0)."

        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=False,
                creation_time=12.5,
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(TypeError) as error:
            batch.configure(
                batch_size=10.6,
                creation_time=12.5,
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, type_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.configure(
                batch_size=0,
                creation_time=12.5,
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, value_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

        with self.assertRaises(ValueError) as error:
            batch.configure(
                batch_size=-10,
                creation_time=12.5,
                timeout_retries=10,
                dynamic=True,
            )
        check_error_message(self, error, value_error)
        self.check_instance(
            batch,
            batch_size=None,
            creation_time=12.5,
            timeout_retries=10,
            batching_type=None,
            recom_num_ref=200,  # does not change if not None
            recom_num_obj=200,  # does not change if not None
        )
        mock_auto_create.assert_not_called()

    def test_pop_methods(self):
        """
        Test the `pop_object` and the `pop_reference`.
        """

        batch = Batch(mock_connection_func())

        # mock BatchRequests
        mock_obj = Mock()
        mock_ref = Mock()
        batch._objects_batch = mock_obj
        batch._reference_batch = mock_ref

        mock_obj.pop.assert_not_called()
        mock_ref.pop.assert_not_called()

        # pop object default value
        batch.pop_object()
        mock_obj.pop.assert_called_with(-1)
        mock_ref.pop.assert_not_called()
        # reset mock objects
        mock_obj.reset_mock()
        mock_ref.reset_mock()

        # pop object at index
        batch.pop_object(10)
        mock_obj.pop.assert_called_with(10)
        mock_ref.pop.assert_not_called()
        # reset mock objects
        mock_obj.reset_mock()
        mock_ref.reset_mock()

        # pop reference default value
        batch.pop_reference()
        mock_obj.pop.assert_not_called()
        mock_ref.pop.assert_called_with(-1)
        # reset mock objects
        mock_obj.reset_mock()
        mock_ref.reset_mock()

        # pop reference at index
        batch.pop_reference(9)
        mock_obj.pop.assert_not_called()
        mock_ref.pop.assert_called_with(9)

    def test_empty_methods(self):
        """
        Test the `empty_objects` and the `empty_references`.
        """

        batch = Batch(mock_connection_func())

        # mock BatchRequests
        mock_obj = Mock()
        mock_ref = Mock()
        batch._objects_batch = mock_obj
        batch._reference_batch = mock_ref

        mock_obj.empty.assert_not_called()
        mock_ref.empty.assert_not_called()

        # empty objects
        batch.empty_objects()
        mock_obj.empty.assert_called()
        mock_ref.empty.assert_not_called()
        # reset mock objects
        mock_obj.reset_mock()
        mock_ref.reset_mock()

        # empty references
        batch.empty_references()
        mock_obj.empty.assert_not_called()
        mock_ref.empty.assert_called()

    def test_is_empty_methods(self):
        """
        Test the `is_empty_objects` and the `is_empty_references`.
        """

        batch = Batch(mock_connection_func())

        # mock BatchRequests
        mock_obj = Mock()
        mock_ref = Mock()
        batch._objects_batch = mock_obj
        batch._reference_batch = mock_ref

        mock_obj.is_empty.assert_not_called()
        mock_ref.is_empty.assert_not_called()

        # check if is_empty objects
        batch.is_empty_objects()
        mock_obj.is_empty.assert_called()
        mock_ref.is_empty.assert_not_called()
        # reset mock objects
        mock_obj.reset_mock()
        mock_ref.reset_mock()

        # check if is_empty reference
        batch.is_empty_references()
        mock_obj.is_empty.assert_not_called()
        mock_ref.is_empty.assert_called()

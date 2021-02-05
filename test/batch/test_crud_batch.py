import unittest
from unittest.mock import patch
from requests import ReadTimeout
from weaviate.batch import ObjectsBatchRequest, ReferenceBatchRequest
from weaviate.batch.crud_batch import Batch 
from weaviate.connect import REST_METHOD_POST
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from test.util import mock_run_rest, check_error_message, check_startswith_error_message

class TestBatch(unittest.TestCase):

    def test_create(self):
        """
        Test the `create` method.
        """

        # invalid calls

        ## error messges
        type_error_message = lambda dt: ("Wrong argument type, expected a sub-class of BatchRequest "
                    f"(ObjectsBatchRequest or ReferenceBatchRequest), got: {dt}")
        requests_error_message = 'Test! Connection error, batch was not added to weaviate.'
        read_timeout_error_message = ("The ReferenceBatchRequest was cancelled because it took "
                "longer than the configured timeout of 100s. "
                "Try reducing the batch size (currently 0) to a lower value. "
                "Aim to on average complete batch request within less than 10s")
        unexpected_error_message = lambda data: f"Create {data} in batch"

        ## test TypeError
        mock_connection = mock_run_rest(side_effect=RequestsConnectionError('Test!'))
        batch = Batch(mock_connection)
        with self.assertRaises(TypeError) as error:
            batch.create(1234)
        check_startswith_error_message(self, error, type_error_message(int))
        mock_connection.run_rest.assert_not_called()

        ## test RequestsConnectionError
        with self.assertRaises(RequestsConnectionError) as error:
            batch.create(ObjectsBatchRequest())
        check_startswith_error_message(self, error, requests_error_message)
        mock_connection.run_rest.assert_called_with(
            path="/batch/objects",
            rest_method=REST_METHOD_POST,
            weaviate_object={"fields": ["ALL"], "objects": []}
        )

        ## test ReadTimeout
        mock_connection = mock_run_rest(side_effect = ReadTimeout('Test!'))
        mock_connection.timeout_config = (2, 100)
        batch = Batch(mock_connection)
        with self.assertRaises(ReadTimeout) as error:
            batch.create(ReferenceBatchRequest())
        check_startswith_error_message(self, error, read_timeout_error_message)
        mock_connection.run_rest.assert_called_with(
            path="/batch/references",
            rest_method=REST_METHOD_POST,
            weaviate_object=[]
        )

        ## test status_code != 200
        mock_connection = mock_run_rest(status_code=204)
        batch = Batch(mock_connection)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            batch.create(ReferenceBatchRequest())
        check_startswith_error_message(self, error, unexpected_error_message('references'))
        mock_connection.run_rest.assert_called_with(
            path="/batch/references",
            rest_method=REST_METHOD_POST,
            weaviate_object=[]
        )

        # valid calls

        ## test status_code == 200
        mock_connection = mock_run_rest(status_code=200)
        batch = Batch(mock_connection)
        batch.create(ReferenceBatchRequest())
        mock_connection.run_rest.assert_called_with(
            path="/batch/references",
            rest_method=REST_METHOD_POST,
            weaviate_object=[]
        )

    @patch('weaviate.batch.crud_batch.Batch.create')
    def test_create_objects(self, mock_create):
        """
        Test the `create_objects` method.

        Parameters
        ----------
        mock_create : unittest.MagicMock
            Mocked `create` method.
        """

        batch = Batch(None)

        # invalid calls
        ## error messages
        type_error_message = lambda dt: ("'objects_batch_request' should be of type "
                f"ObjectsBatchRequest but was given : {dt}")

        ## wrong type ReferenceBatchRequest
        with self.assertRaises(TypeError) as error:
            batch.create_objects(ReferenceBatchRequest())
        check_error_message(self, error, type_error_message(ReferenceBatchRequest))
        mock_create.assert_not_called()

        ## wrong type int
        with self.assertRaises(TypeError) as error:
            batch.create_objects(123)
        check_error_message(self, error, type_error_message(int))
        mock_create.assert_not_called()

        # valid calls

        obj = ObjectsBatchRequest()
        batch.create_objects(obj)
        mock_create.assert_called_with(
            batch_request=obj
        )

    @patch('weaviate.batch.crud_batch.Batch.create')
    def test_create_references(self, mock_create):
        """
        Test the `create_references` method.

        Parameters
        ----------
        mock_create : unittest.MagicMock
            Mocked `create` method.
        """

        batch = Batch(None)

        # invalid calls
        ## error messages
        type_error_message = lambda dt: ("'reference_batch_request' should be of type "
                f"ReferenceBatchRequest but was given : {dt}")

        ## wrong type ObjectsBatchRequest
        with self.assertRaises(TypeError) as error:
            batch.create_references(ObjectsBatchRequest())
        check_error_message(self, error, type_error_message(ObjectsBatchRequest))
        mock_create.assert_not_called()

        ## wrong type int
        with self.assertRaises(TypeError) as error:
            batch.create_references(123)
        check_error_message(self, error, type_error_message(int))
        mock_create.assert_not_called()

        # valid calls

        obj = ReferenceBatchRequest()
        batch.create_references(obj)
        mock_create.assert_called_with(
            batch_request=obj
        )

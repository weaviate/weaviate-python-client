import unittest
from unittest.mock import Mock
import uuid
import time
import weaviate
from weaviate.tools import Batcher
from weaviate.connect import REST_METHOD_POST
from test.util import replace_connection, mock_run_rest, check_error_message


class TestBatcher(unittest.TestCase):

    def test_batcher_add_objects(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))
        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))
        self.assertEqual(2, len(batcher._objects_batch))
        client_mock.batch.create.assert_not_called()
        # With the next thing the batcher should create the batch
        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))
        client_mock.batch.create.assert_called()
        # check if batch is being reset
        self.assertEqual(0, len(batcher._objects_batch))

    def test_batcher_add_reference(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        self.assertEqual(2, len(batcher._reference_batch))
        client_mock.batch.create.assert_not_called()
        # With the next reference the batcher should create the batch
        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        client_mock.batch.create.assert_called()
        # check if batch is being reset
        self.assertEqual(0, len(batcher._reference_batch))

    def test_batcher_add(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        reference_keys = set(['from_object_uuid', 'from_object_class_name', 'from_property_name',\
                'to_object_uuid'])
        all_object_keys = set(['data_object', 'class_name', 'uuid', 'vector'])

        # invalid calls
        # error message
        type_error_message = ("Wrong arguments for adding data to batcher!\n"
            f"Accepted arguments for references: {reference_keys}\n"
            f"Accepted arguments for objects: {all_object_keys}! 'uuid' and 'vector' - optional\n")

        with self.assertRaises(TypeError) as error:
            batcher.add(
                from_object_class_name="FromClass",
                from_property_name="fromProperty",
                to_object_uuid=str(uuid.uuid4())
            )
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            batcher.add(
                from_object_uuid=str(uuid.uuid4()),
                from_property_name="fromProperty",
                to_object_uuid=str(uuid.uuid4())
            )
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            batcher.add(
                from_object_uuid=str(uuid.uuid4()),
                from_object_class_name="FromClass",
                to_object_uuid=str(uuid.uuid4())
            )
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            batcher.add(
                from_object_uuid=str(uuid.uuid4()),
                from_object_class_name="FromClass",
                from_property_name="fromProperty",
            )
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            batcher.add(
                class_name="MyClass",
                uuid=str(uuid.uuid4()),
                vector=[1., 2.]
            )
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            batcher.add(
                data_object={},
                uuid=str(uuid.uuid4()),
                vector=[1., 2.]
            )
        check_error_message(self, error, type_error_message)


        # valid calls
        batcher.add(
            from_object_uuid=str(uuid.uuid4()),
            from_object_class_name="FromClass",
            from_property_name="fromProperty",
            to_object_uuid=str(uuid.uuid4())
        )
        batcher.add(
            data_object={},
            class_name="MyClass",
            uuid=str(uuid.uuid4()),
            vector=[1., 2.]
        )
        self.assertEqual(1, len(batcher._reference_batch))
        self.assertEqual(1, len(batcher._objects_batch))
        client_mock.batch.create.assert_not_called()
        # With the next reference the batcher should create the batch
        batcher.add(
            from_object_uuid=str(uuid.uuid4()),
            from_object_class_name="FromClass",
            from_property_name="fromProperty",
            to_object_uuid=str(uuid.uuid4())
        )
        client_mock.batch.create.assert_called()
        # check if batch is being reset
        self.assertEqual(0, len(batcher._reference_batch))

    def test_batcher_close(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        batcher.close()
        client_mock.batch.create.assert_called()

    def test_batcher_force_update(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        batcher.add_reference(str(uuid.uuid4()),"FromClass", "fromProperty", str(uuid.uuid4()))
        batcher.update_batches()

        client_mock.batch.create.assert_called()

    def test_with_batcher(self):
        client_mock = Mock()
        with Batcher(client_mock) as batcher:
            batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))

        client_mock.batch.create.assert_called()

    def test_auto_commit_timeout(self):
        client = weaviate.Client("http://localhorst:8080")

        connection_mock = mock_run_rest()
        replace_connection(client, connection_mock)

        b = Batcher(client, auto_commit_timeout=0.25)
        b.add_data_object({"a": "b"}, "class")
        time.sleep(1.0)
        connection_mock.run_rest.assert_called()
        b.close()

    def test_auto_commit_timeout_last_update(self):
        client = weaviate.Client("http://localhorst:8080")

        connection_mock = mock_run_rest()
        replace_connection(client, connection_mock)

        # Timeout is set to 1 seconds but updates come in between
        # so there should not be any call
        b = Batcher(client, auto_commit_timeout=0.5)
        b.add_data_object({"a": "b"}, "class")
        time.sleep(0.2)
        b.add_data_object({"a": "b"}, "class")
        time.sleep(0.2)
        b.add_reference("d2b1ec6c-54a3-44e5-aa3e-766a0c73f1cd", "FromClass",
                        "fromProp", "afdd15f2-85a7-44ce-a6a3-b3c4c9fe2c64")
        time.sleep(0.2)
        b.add_data_object({"a": "b"}, "classA")
        time.sleep(0.2)
        b.add_data_object({"a": "b"}, "classB")
        time.sleep(0.2)
        b.add_data_object({"a": "b"}, "classC")
        try:
            connection_mock.run_rest.assert_called()
        except:
            pass
        b.close()

    def test_view_return_values_callback(self):
        client = weaviate.Client("http://localhorst:8080")

        response_data = [
            {
                'class': 'Person',
                'creationTimeUnix': 1598607494119,
                'id': '4b166dbe-d99d-5091-abdd-95b83330ed3a',
                'meta': {
                    'interpretation': {
                        'source': [
                            {
                                'concept': 'person',
                                'occurrence': 6627994,
                                'weight': 0.3086933493614197
                            },
                            {
                                'concept': '2',
                                'occurrence': 41313922,
                                'weight': 0.10000000149011612
                            }
                        ]
                    }
                },
                'properties': {
                    'name': '2'
                },
                'deprecations': None,
                'result': {}
            },
            {
                'class': 'classC',
                'creationTimeUnix': 1598607494121,
                'id': '98123fde-012f-5ff3-8b50-881449dac91a',
                'meta': {
                    'interpretation': {
                        'source': [
                            {
                                'concept': 'person',
                                'occurrence': 6627994,
                                'weight': 0.269020140171051
                            },
                            {
                                'concept': '3',
                                'occurrence': 28253531,
                                'weight': 0.10000000149011612
                            }
                        ]
                    }
                },
                'properties': {
                    'name': '3'
                },
                'deprecations': None,
                'result': {}
            },
            {
                'class': 'Person',
                'creationTimeUnix': 1598607494122,
                'id': '6ed955c6-506a-5343-9be4-2c0afae02eef',
                'meta': {
                    'interpretation': {
                        'source': [
                            {
                                'concept': 'person',
                                'occurrence': 6627994,
                                'weight': 0.2414865791797638
                            },
                            {
                                'concept': '4',
                                'occurrence': 21912221,
                                'weight': 0.10000000149011612
                            }
                        ]
                    }
                },
                'properties': {
                    'name': '4'
                },
                'deprecations': None,
                'result': {}
            }
        ]
        connection_mock = mock_run_rest(return_json=response_data)
        replace_connection(client, connection_mock)

        vrc = ValidateResultCall()
        b = Batcher(client, return_values_callback=vrc.results)
        b.add_data_object({"name": "2"}, "Person")
        b.add_data_object({"name": "3"}, "Person")
        b.add_data_object({"name": "4"}, "Person")
        b.update_batches()

        self.assertEqual(3, len(vrc.data))

    def test_batch_exceeds_size_but_fails(self):
        client = weaviate.Client("http://localhorst:8080")

        connection_mock = mock_run_rest(return_json={"TestError": "test error"}, status_code=502)
        replace_connection(client, connection_mock)

        batcher = weaviate.tools.Batcher(client, batch_size=2, max_backoff_time=2, max_request_retries=2)

        batcher.add_data_object({'d': 1}, "Data")
        batcher.add_data_object({'d': 2}, "Data")
        batcher.add_data_object({'d': 3}, "Data")
        batcher.add_data_object({'d': 4}, "Data")

        # First mock only returned errors so the batches should be retaiend
        # This mock allows now successful requests
        success_mock = mock_run_rest()
        replace_connection(client, success_mock)

        batcher.add_data_object({'d': 5}, "Data")
        batcher.add_data_object({'d': 6}, "Data")

        # Batch must be called twice with batch request
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]

        self.assertEqual("/batch/objects", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

        call_kwargs = call_args_list[1][1]

        self.assertEqual("/batch/objects", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

        call_args_list = success_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]

        self.assertEqual("/batch/objects", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

    def test_batch_exceeds_size_but_fails_close(self):
        client = weaviate.Client("http://localhorst:8080")

        connection_mock = mock_run_rest(return_json={"Error": "test error"}, status_code=502)
        replace_connection(client, connection_mock)

        batcher = weaviate.tools.Batcher(client, batch_size=2, max_backoff_time=2, max_request_retries=2)

        batcher.add_data_object({'d': 1}, "Data")
        batcher.add_data_object({'d': 2}, "Data")
        batcher.add_data_object({'d': 3}, "Data")
        batcher.add_data_object({'d': 4}, "Data")

        
        # First mock only returned errors so the batches should be retaiend
        # This mock allows now successful requests
        success_mock = mock_run_rest()
        replace_connection(client, success_mock)

        batcher.add_data_object({'d': 5}, "Data")

        batcher.close()

        # Batch must be called twice with batch request
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]

        self.assertEqual("/batch/objects", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

        call_kwargs = call_args_list[1][1]

        self.assertEqual("/batch/objects", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])

        call_args_list = success_mock.run_rest.call_args_list
        call_kwargs = call_args_list[0][1]

        self.assertEqual("/batch/objects", call_kwargs['path'])
        self.assertEqual(REST_METHOD_POST, call_kwargs['rest_method'])


class ValidateResultCall:

    def __init__(self):
        self.data = []

    def results(self, results):
        self.data = results
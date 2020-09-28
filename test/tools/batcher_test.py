import unittest
import weaviate
from weaviate.tools import Batcher
from weaviate import SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_ACTIONS
import uuid
from unittest.mock import Mock
from test.testing_util import replace_connection, add_run_rest_to_mock
import time
from weaviate.connect import REST_METHOD_POST


class TestBatcher(unittest.TestCase):

    def test_batcher_add_thing(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))
        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))
        self.assertEqual(2, len(batcher._things_batch))
        assert not client_mock.batch.create_things.called
        # With the next thing the batcher should create the batch
        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))
        assert client_mock.batch.create_things.called
        # check if batch is being reset
        self.assertEqual(0, len(batcher._things_batch))

    def test_batcher_add_action(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()), SEMANTIC_TYPE_ACTIONS)
        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()), SEMANTIC_TYPE_ACTIONS)
        self.assertEqual(2, len(batcher._actions_batch))
        assert not client_mock.batch.create_actions.called
        # With the next thing the batcher should create the batch
        batcher.add_data_object({}, "MyClass", str(uuid.uuid4()), SEMANTIC_TYPE_ACTIONS)
        assert client_mock.batch.create_actions.called
        # check if batch is being reset
        self.assertEqual(0, len(batcher._things_batch))

    def test_batcher_add_reference(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        self.assertEqual(2, len(batcher._reference_batch))
        assert not client_mock.batch.add_references.called
        # With the next reference the batcher should create the batch
        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        assert client_mock.batch.add_references.called
        # check if batch is being reset
        self.assertEqual(0, len(batcher._reference_batch))

    def test_batcher_close(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        batcher.close()
        assert client_mock.batch.add_references.called

    def test_batcher_force_update(self):
        client_mock = Mock()
        batcher = Batcher(client_mock, 3)

        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        batcher.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", str(uuid.uuid4()), "fromProperty",
                              SEMANTIC_TYPE_THINGS, str(uuid.uuid4()))
        batcher.update_batches()

        assert client_mock.batch.add_references.called

    def test_with_batcher(self):
        client_mock = Mock()
        with Batcher(client_mock) as batcher:
            batcher.add_data_object({}, "MyClass", str(uuid.uuid4()))

        assert client_mock.batch.create_things.called

    def test_auto_commit_timeout(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        b = Batcher(w, auto_commit_timeout=0.25)
        b.add_data_object({"a": "b"}, "class")
        time.sleep(1.0)
        connection_mock.run_rest.assert_called()
        b.close()

    def test_auto_commit_timeout_last_update(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        # Timeout is set to 1 seconds but updates come in between
        # so there should not be any call
        b = Batcher(w, auto_commit_timeout=0.5)
        b.add_data_object({"a": "b"}, "class")
        time.sleep(0.2)
        b.add_data_object({"a": "b"}, "class", semantic_type=SEMANTIC_TYPE_ACTIONS)
        time.sleep(0.2)
        b.add_reference(SEMANTIC_TYPE_THINGS, "FromClass", "d2b1ec6c-54a3-44e5-aa3e-766a0c73f1cd",
                        "fromProp", SEMANTIC_TYPE_ACTIONS, "afdd15f2-85a7-44ce-a6a3-b3c4c9fe2c64")
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
        w = weaviate.Client("http://localhorst:8080")

        response_data = [{'class': 'Person', 'creationTimeUnix': 1598607494119, 'id': '4b166dbe-d99d-5091-abdd-95b83330ed3a', 'meta': {'interpretation': {'source': [{'concept': 'person', 'occurrence': 6627994, 'weight': 0.3086933493614197}, {'concept': '2', 'occurrence': 41313922, 'weight': 0.10000000149011612}]}}, 'schema': {'name': '2'}, 'deprecations': None, 'result': {}}, {'class': 'classC', 'creationTimeUnix': 1598607494121, 'id': '98123fde-012f-5ff3-8b50-881449dac91a', 'meta': {'interpretation': {'source': [{'concept': 'person', 'occurrence': 6627994, 'weight': 0.269020140171051}, {'concept': '3', 'occurrence': 28253531, 'weight': 0.10000000149011612}]}}, 'schema': {'name': '3'}, 'deprecations': None, 'result': {}}, {'class': 'Person', 'creationTimeUnix': 1598607494122, 'id': '6ed955c6-506a-5343-9be4-2c0afae02eef', 'meta': {'interpretation': {'source': [{'concept': 'person', 'occurrence': 6627994, 'weight': 0.2414865791797638}, {'concept': '4', 'occurrence': 21912221, 'weight': 0.10000000149011612}]}}, 'schema': {'name': '4'}, 'deprecations': None, 'result': {}}]
        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, response_data)
        replace_connection(w, connection_mock)

        vrc = ValidateResultCall()
        b = Batcher(w, return_values_callback=vrc.results)
        b.add_data_object({"name": "2"}, "Person")
        b.add_data_object({"name": "3"}, "Person")
        b.add_data_object({"name": "4"}, "Person")
        b.update_batches()

        self.assertEqual(3, len(vrc.data))

    def test_batch_exceeds_size_but_fails(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {"Error": "test error"}, 502)
        replace_connection(w, connection_mock)

        batcher = weaviate.tools.Batcher(w, batch_size=2, max_backoff_time=2, max_request_retries=2)

        batcher.add_data_object({'d': 1}, "Data")
        batcher.add_data_object({'d': 2}, "Data")
        batcher.add_data_object({'d': 3}, "Data")
        batcher.add_data_object({'d': 4}, "Data")

        success_mock = Mock()
        # First mock only returned errors so the batches should be retaiend
        # This mock allows now successful requests
        add_run_rest_to_mock(success_mock)
        replace_connection(w, success_mock)

        batcher.add_data_object({'d': 5}, "Data")
        batcher.add_data_object({'d': 6}, "Data")

        # Batch must be called twice with batch request
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/batching/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])

        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/batching/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])

        call_args_list = success_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]
        self.assertEqual("/batching/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])

    def test_batch_exceeds_size_but_fails_close(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, {"Error": "test error"}, 502)
        replace_connection(w, connection_mock)

        batcher = weaviate.tools.Batcher(w, batch_size=2, max_backoff_time=2, max_request_retries=2)

        batcher.add_data_object({'d': 1}, "Data")
        batcher.add_data_object({'d': 2}, "Data")
        batcher.add_data_object({'d': 3}, "Data")
        batcher.add_data_object({'d': 4}, "Data")

        success_mock = Mock()
        # First mock only returned errors so the batches should be retaiend
        # This mock allows now successful requests
        add_run_rest_to_mock(success_mock)
        replace_connection(w, success_mock)

        batcher.add_data_object({'d': 5}, "Data")

        batcher.close()

        # Batch must be called twice with batch request
        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/batching/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])

        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/batching/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])

        call_args_list = success_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]
        self.assertEqual("/batching/things", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])


class ValidateResultCall:

    def __init__(self):
        self.data = []

    def results(self, results):
        self.data = results
import unittest
import weaviate
from test.testing_util import add_run_rest_to_mock, replace_connection
from weaviate.connect import REST_METHOD_DELETE, REST_METHOD_GET
from weaviate import UnexpectedStatusCodeException, SEMANTIC_TYPE_ACTIONS
from unittest.mock import Mock


class TestDelete(unittest.TestCase):

    def test_delete_thing_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.data_object.delete(4)
            self.fail("UUID has the wrong type")
        except TypeError:
            pass

        try:
            w.data_object.delete("Hallo Wereld")
            self.fail("UUID has the wrong value")
        except ValueError:
            pass

    def test_delete_thing(self):
        w = weaviate.Client("http://localhost:8080")

        # 1. Succesfully delete something
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, status_code=204)
        replace_connection(w, connection_mock)

        thing = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        w.data_object.delete(thing)

        connection_mock.run_rest.assert_called_with("/things/"+thing, REST_METHOD_DELETE)

        # 2. Delete something that does not exist
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, status_code=404)
        replace_connection(w, connection_mock)

        thing = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        try:
            w.data_object.delete(thing)
            self.fail("Unexpected status code")
        except UnexpectedStatusCodeException:
            pass

        connection_mock.run_rest.assert_called_with("/things/" + thing, REST_METHOD_DELETE)

    def test_get_thing_by_id(self):
        w = weaviate.Client("http://localhost:8080")

        thing = {
            "name": "test"
        }
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, return_json=thing, status_code=200)
        replace_connection(w, connection_mock)

        result = w.data_object.get_by_id("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertIn("name", result)

    def test_get_underscore_properties(self):
        w = weaviate.Client("http://localhorst:8080")

        return_value = {
            "_interpretation": {
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
            },
            "_vector": [0.095590845, 0.24995095, -0.19630778],
            "class": "Person",
            "creationTimeUnix": 1599550471320,
            "id": "1c9cd584-88fe-5010-83d0-017cb3fcb446",
            "lastUpdateTimeUnix": 1599550471320,
            "meta": {
                "vector": [0.095590845, 0.24995095, 0.11117377]
            },
            "schema": {
                "name": "Alan Turing"
            },
            "vectorWeights": None
        }

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, return_value)
        replace_connection(w, connection_mock)

        result = w.data_object.get_by_id("21fa7bc8-011f-4066-861e-f62c285f09c8",
                                         underscore_properties=["_vector", "_interpretation"])

        self.assertEqual(return_value, result)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/things/21fa7bc8-011f-4066-861e-f62c285f09c8", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])
        self.assertEqual({"include": "_vector,_interpretation"}, call_kwargs["params"])

    def test_get_all_things(self):
        return_value_get_all_things = {
            "deprecations": None,
            "things": [
                {
                    "class": "Group",
                    "creationTimeUnix": 1599550471404,
                    "id": "2db436b5-0557-5016-9c5f-531412adf9c6",
                    "lastUpdateTimeUnix": 1599550471404,
                    "schema": {
                        "members": [
                            {
                                "beacon": "weaviate://localhost/things/b36268d4-a6b5-5274-985f-45f13ce0c642",
                                "href": "/v1/things/b36268d4-a6b5-5274-985f-45f13ce0c642"
                            },
                            {
                                "beacon": "weaviate://localhost/things/1c9cd584-88fe-5010-83d0-017cb3fcb446",
                                "href": "/v1/things/1c9cd584-88fe-5010-83d0-017cb3fcb446"
                            }
                        ],
                        "name": "Legends"
                    },
                    "vectorWeights": None
                },
                {
                    "class": "Person",
                    "creationTimeUnix": 1599550471320,
                    "id": "1c9cd584-88fe-5010-83d0-017cb3fcb446",
                    "lastUpdateTimeUnix": 1599550471320,
                    "schema": {
                        "name": "Alan Turing"
                    },
                    "vectorWeights": None
                },
                {
                    "class": "Person",
                    "creationTimeUnix": 1599550470957,
                    "id": "b36268d4-a6b5-5274-985f-45f13ce0c642",
                    "lastUpdateTimeUnix": 1599550470957,
                    "schema": {
                        "name": "John von Neumann"
                    },
                    "vectorWeights": None
                }
            ],
            "totalResults": 3
        }

        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, return_value_get_all_things)
        replace_connection(w, connection_mock)

        result = w.data_object.get()
        self.assertEqual(return_value_get_all_things["things"], result)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/things", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])

    def test_get_all_actions(self):
        w = weaviate.Client("http://localhorst:8080")

        result_empty_actions = {
            "actions": [],
            "deprecations": None
        }

        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, result_empty_actions)
        replace_connection(w, connection_mock)

        result = w.data_object.get(semantic_type=SEMANTIC_TYPE_ACTIONS)
        self.assertEqual([], result)

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/actions", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])

    def test_get_all_including_underscore_properties(self):
        w = weaviate.Client("http://localhorst:8080")

        result_empty_actions = {
            "actions": [],
            "deprecations": None
        }

        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, result_empty_actions)
        replace_connection(w, connection_mock)

        result = w.data_object.get(["_vector", "_nearestNeighbors"], SEMANTIC_TYPE_ACTIONS)
        self.assertEqual([], result)

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/actions", call_args[0])
        self.assertEqual(REST_METHOD_GET, call_args[1])
        self.assertEqual({"include": "_vector,_nearestNeighbors"}, call_kwargs["params"])

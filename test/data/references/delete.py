import unittest
import weaviate
from unittest.mock import Mock
from test.testing_util import replace_connection, add_run_rest_to_mock
from weaviate import SEMANTIC_TYPE_ACTIONS
from weaviate.connect import REST_METHOD_DELETE


class TestRemoveReference(unittest.TestCase):

    def test_delete_reference_from_thing_input(self, ):
        w = weaviate.Client("http://localhost:8080")

        uuid_1 = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        uuid_2 = "a36268d4-a6b5-5274-985f-45f13ce0c642"

        try:
            w.data_object.reference.delete(1, "myProperty", uuid_2)
            self.fail("UUID has the wrong type")
        except TypeError:
            pass
        try:
            w.data_object.reference.delete(uuid_1, "myProperty", 2)
            self.fail("UUID has the wrong type")
        except TypeError:
            pass
        try:
            w.data_object.reference.delete(uuid_1, 3, uuid_2)
            self.fail("Property name has the wrong type")
        except TypeError:
            pass
        try:
            w.data_object.reference.delete("str", "myProperty", uuid_2)
            self.fail("UUID has the wrong value")
        except ValueError:
            pass
        try:
            w.data_object.reference.delete(uuid_1, "myProperty", "str")
            self.fail("UUID has the wrong value")
        except ValueError:
            pass
        try:
            w.data_object.reference.delete(uuid_1, "myProperty", uuid_2, to_weaviate=4)
            self.fail("to_weaviate has the wrong type")
        except TypeError:
            pass

    def test_delete_reference_from_thing(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=204)
        replace_connection(w, connection_mock)

        w.data_object.reference.delete("08f2af9a-78ae-41a6-94de-6ac19392fe2e", "myProperty",
                                       "a36268d4-a6b5-5274-985f-45f13ce0c642")

        w.data_object.reference.delete("7591be77-5959-4386-9828-423fc5096e87",
                                    "hasItem", "http://localhost:8080/v1/actions/1cd80c11-29f0-453f-823c-21547b1511f0",
                                    to_semantic_type=SEMANTIC_TYPE_ACTIONS)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list

        call_args, call_kwargs = call_args_list[0]
        self.assertEqual("/things/08f2af9a-78ae-41a6-94de-6ac19392fe2e/references/myProperty", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])
        self.assertEqual({"beacon": "weaviate://localhost/things/a36268d4-a6b5-5274-985f-45f13ce0c642"}, call_args[2])

        call_args, call_kwargs = call_args_list[1]
        self.assertEqual("/things/7591be77-5959-4386-9828-423fc5096e87/references/hasItem", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])
        self.assertEqual({"beacon": "weaviate://localhost/actions/1cd80c11-29f0-453f-823c-21547b1511f0"}, call_args[2])

        


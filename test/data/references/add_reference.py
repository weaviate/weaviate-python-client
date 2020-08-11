import unittest
import weaviate
from unittest.mock import Mock
from test.testing_util import replace_connection, add_run_rest_to_mock
from weaviate import SEMANTIC_TYPE_ACTIONS
from weaviate.connect import REST_METHOD_POST, REST_METHOD_PUT


class TestAddReference(unittest.TestCase):

    def test_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.data_object.reference.add(1, "prop", "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.data_object.reference.add("67972f90-1912-4464-af51-2e9a1b42f6d6", 1, "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.data_object.reference.add("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", 1)
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.data_object.reference.add("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", 1)
            self.fail("Expected to fail with error")
        except TypeError:
            pass

        try:
            w.data_object.reference.add("my UUID", "prop", "7eacfab8-c803-46dd-8edf-47895303a796")
            self.fail("Expected to fail with error")
        except ValueError:
            pass

        try:
            w.data_object.reference.add("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop",
                            "7eacfab8-c803-46dd-8edf-47895303a796", "thing")
            self.fail("Expected to fail with error")
        except ValueError:
            pass

        try:
            w.data_object.reference.add("67972f90-1912-4464-af51-2e9a1b42f6d6", "prop", "my uuid")
            self.fail("Expected to fail with error")
        except ValueError:
            pass

        try:
            # URL semantic type and explicit semantic type are different
            w.data_object.reference.add("http://localhost:8080/v1/things/7591be77-5959-4386-9828-423fc5096e87", "prop",
                                        "http://localhost:8080/v1/things/3250b0b8-eaf7-499b-ac68-9084c9c82d0f",
                                        from_semantic_type=SEMANTIC_TYPE_ACTIONS)
            self.fail("Expected to fail with error")
        except ValueError:
            pass

        try:
            # URL semantic type and explicit semantic type are different
            w.data_object.reference.add("http://localhost:8080/v1/things/7591be77-5959-4386-9828-423fc5096e87", "prop",
                                        "http://localhost:8080/v1/things/3250b0b8-eaf7-499b-ac68-9084c9c82d0f",
                                        to_semantic_type=SEMANTIC_TYPE_ACTIONS)
            self.fail("Expected to fail with error")
        except ValueError:
            pass

    def test_add_reference(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        # 1. Plain
        w.data_object.reference.add("3250b0b8-eaf7-499b-ac68-9084c9c82d0f",
                                    "hasItem", "99725f35-f12a-4f36-a2e2-0d41501f4e0e")

        # 2. from actions
        w.data_object.reference.add("7c4efed4-f38b-4f6f-abbe-b8801128f4b5",
                                    "hasItem", "1140b9d7-6335-49c9-92e0-3029f1cf1862",
                                    from_semantic_type=SEMANTIC_TYPE_ACTIONS)

        # 3. using url
        w.data_object.reference.add("http://localhost:8080/v1/things/7591be77-5959-4386-9828-423fc5096e87",
                                    "hasItem", "http://localhost:8080/v1/things/1cd80c11-29f0-453f-823c-21547b1511f0")

        # 4. using weavaite url
        w.data_object.reference.add("weaviate://localhost/things/f8def983-87e7-4e21-bf10-e32e2de3efcf",
                                    "hasItem", "weaviate://localhost/things/e40aaef5-d3e5-44f1-8ec4-3eafc8475078")

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list

        # 1.
        call_args, call_kwargs = call_args_list[0]
        self.assertEqual("/things/3250b0b8-eaf7-499b-ac68-9084c9c82d0f/references/hasItem", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual({'beacon': 'weaviate://localhost/things/99725f35-f12a-4f36-a2e2-0d41501f4e0e'}, call_args[2])

        # 2.
        call_args, call_kwargs = call_args_list[1]
        self.assertEqual("/actions/7c4efed4-f38b-4f6f-abbe-b8801128f4b5/references/hasItem", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual({'beacon': 'weaviate://localhost/things/1140b9d7-6335-49c9-92e0-3029f1cf1862'}, call_args[2])

        # 3.
        call_args, call_kwargs = call_args_list[2]
        self.assertEqual("/things/7591be77-5959-4386-9828-423fc5096e87/references/hasItem", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual({'beacon': 'weaviate://localhost/things/1cd80c11-29f0-453f-823c-21547b1511f0'}, call_args[2])

        # 4.
        call_args, call_kwargs = call_args_list[3]
        self.assertEqual("/things/f8def983-87e7-4e21-bf10-e32e2de3efcf/references/hasItem", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual({'beacon': 'weaviate://localhost/things/e40aaef5-d3e5-44f1-8ec4-3eafc8475078'}, call_args[2])

    def test_replace_reference(self):
        # PUT needs a beacon array while POST needs a single beacon dict
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        w.data_object.reference.replace("de998e81-fa66-440e-a1de-2a2013667e77", "hasAwards",
                                        "fc041624-4ddf-4b76-8e09-a5b0b9f9f832")

        w.data_object.reference.replace("4e44db9b-7f9c-4cf4-a3a0-b57024eefed0", "hasAwards",
                                        ["17ee17bd-a09a-49ff-adeb-d242f25f390d",
                                         "f8c25386-707c-40c0-b7b9-26cc0e9b2bd1",
                                         "d671dc52-dce4-46e7-8731-b722f19420c8"])

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/things/de998e81-fa66-440e-a1de-2a2013667e77/references/hasAwards", call_args[0])
        self.assertEqual(REST_METHOD_PUT, call_args[1])
        self.assertEqual([{'beacon': 'weaviate://localhost/things/fc041624-4ddf-4b76-8e09-a5b0b9f9f832'}], call_args[2])

        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/things/4e44db9b-7f9c-4cf4-a3a0-b57024eefed0/references/hasAwards", call_args[0])
        self.assertEqual(REST_METHOD_PUT, call_args[1])
        self.assertEqual([{'beacon': 'weaviate://localhost/things/17ee17bd-a09a-49ff-adeb-d242f25f390d'},
                          {'beacon': 'weaviate://localhost/things/f8c25386-707c-40c0-b7b9-26cc0e9b2bd1'},
                          {'beacon': 'weaviate://localhost/things/d671dc52-dce4-46e7-8731-b722f19420c8'}], call_args[2])

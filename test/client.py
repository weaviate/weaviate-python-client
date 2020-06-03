import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.testing_util import *
import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
    from mock import patch
else:
    from unittest.mock import Mock
    from unittest.mock import patch


class TestWeaviateClient(unittest.TestCase):
    def test_create_weaviate_object_wrong_url(self):
        try:
            w = weaviate.Client(None)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Client(42)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Client("")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected
        try:
            w = weaviate.Client("hallo\tasdf")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected

    def test_create_weaviate_object_create_valid_object(self):
        try:
            w = weaviate.Client("http://localhost:8080")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Client("http://localhost:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Client("http://test.domain/path:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        with patch('weaviate.connect.connection.requests') as requests_mock:
            return_value_get_method = Mock()
            return_value_get_method.configure_mock(status_code=404)
            requests_mock.get.return_value = return_value_get_method
            try:
                w = weaviate.Client("http://35.205.175.0:80")
            except Exception as e:
                self.fail("Unexpected exception: " + str(e))


    def test_is_reachable(self):
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        # Request to weaviate returns 200
        w._connection = add_run_rest_to_mock(connection_mock)
        self.assertTrue(w.is_reachable())  # Should be true

        # Test exception in connect
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w._connection = connection_mock
        self.assertFalse(w.is_reachable())


    def test_input_checking(self):
        w = weaviate.Client("http://localhost:8080/")
        self.assertEqual("http://localhost:8080/v1", w._connection.url, "Should remove trailing slash")

    def test_client_config(self):
        # The client config is supposed to just be a model.
        # The checking of the validity of the values should happen in the client.

        # Should work
        timeout = (3, 60)
        config = weaviate.ClientConfig(timeout_config=timeout)
        w = weaviate.Client("http://localhost:8080", client_config=config)
        self.assertEqual(timeout, w._connection.timeout_config)

        try:
            config = weaviate.ClientConfig(timeout_config="very long timeout")
            weaviate.Client("http://localhost:8080", client_config=config)
            self.fail("Should throw error")
        except TypeError:
            pass

        # Too long tupel
        try:
            config = weaviate.ClientConfig(timeout_config=(3, 4, 5))
            weaviate.Client("http://localhost:8080", client_config=config)
            self.fail("Should throw error")
        except ValueError:
            pass

        # tupel of wrong kind
        try:
            config = weaviate.ClientConfig(timeout_config=("many", "short"))
            weaviate.Client("http://localhost:8080", client_config=config)
            self.fail("Should throw error")
        except TypeError:
            pass

    def test_add_reference_to_thing_types(self):
        w = weaviate.Client("http://localhost:8081")
        # Type errors:
        try:
            w.add_reference_from_thing_to_thing(1,
                                     "hasReference",
                                     "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
            self.fail("Should throw error")
        except TypeError:
            pass
        try:
            w.add_reference_from_thing_to_thing("686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                                1,
                                     "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
            self.fail("Should throw error")
        except TypeError:
            pass
        try:
            w.add_reference_from_thing_to_thing("686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                     "hasReference",
                                                1)
            self.fail("Should throw error")
        except TypeError:
            pass
        # Value errors:
        try:
            w.add_reference_from_thing_to_thing("dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                     "hasReference",
                                     "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
            self.fail("Should throw error")
        except ValueError:
            pass
        try:
            w.add_reference_from_thing_to_thing("686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                     "",
                                     "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
            self.fail("Should throw error")
        except ValueError:
            pass
        try:
            w.add_reference_from_thing_to_thing("686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                     "hasReference",
                                     "f61b-b524-45e0-9bbe-2c1550bf73d2")
            self.fail("Should throw error")
        except ValueError:
            pass
        try:
            w.add_reference_from_thing_to_thing("weaviate://localhost/things/686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                     "hasReference",
                                     "weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2",
                                     "otherdomain.com")
            self.fail("to_thing_uuid is an url but the domain does not macht to_weaviate")
        except ValueError:
            pass

    def test_add_reference_to_thing(self):
        w = weaviate.Client("http://localhost:8081")
        connection_mock = Mock()
        w._connection = add_run_rest_to_mock(connection_mock, None, status_code=200)

        # Add reference using uuids
        w.add_reference_from_thing_to_thing("686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                 "hasReference",
                                 "28f3f61b-b524-45e0-9bbe-2c1550bf73d2")

        connection_mock.run_rest.assert_called_with(
            '/things/686dcd1d-573b-4fba-bbb9-f63fa9a6926b/references/hasReference',
            REST_METHOD_POST,
            {'beacon': 'weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'})

        # Add reference using urls local host
        w.add_reference_from_thing_to_thing("weaviate://localhost/things/686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                 "hasReference",
                                 "weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2")

        connection_mock.run_rest.assert_called_with(
            '/things/686dcd1d-573b-4fba-bbb9-f63fa9a6926b/references/hasReference',
            REST_METHOD_POST,
            {'beacon': 'weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'})

        # Add reference using urls local host
        w.add_reference_from_thing_to_thing("weaviate://peoplesfrontofjudea.org/things/686dcd1d-573b-4fba-bbb9-f63fa9a6926b",
                                 "hasReference",
                                 "weaviate://judeanpeoplesfront.org/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2",
                                            None)

        connection_mock.run_rest.assert_called_with(
            '/things/686dcd1d-573b-4fba-bbb9-f63fa9a6926b/references/hasReference',
            REST_METHOD_POST,
            {'beacon': 'weaviate://judeanpeoplesfront.org/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2'})




if __name__ == '__main__':
    unittest.main()

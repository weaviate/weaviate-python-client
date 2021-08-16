import unittest
from unittest.mock import patch, Mock
import json
from weaviate.auth import AuthClientPassword
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError, AuthenticationFailedException
from weaviate.wcs import WCS
from test.util import check_error_message, check_startswith_error_message


class TestWCS(unittest.TestCase):

    @patch('weaviate.wcs.crud_wcs.WCS._set_bearer')
    def test___init__(self, mock_set_bearer):
        """
        Test the `__init__` method.
        """
        # invalid calls
        ## error messages
        login_error_message = (
                "No login credentials provided, or wrong type of credentials! "
                "Accepted type of credentials: weaviate.auth.AuthClientPassword"
            )

        with self.assertRaises(AuthenticationFailedException) as error:
            WCS(None)
        check_error_message(self, error, login_error_message)
        mock_set_bearer.assert_not_called()

        # valid calls
        # without DEV
        auth = AuthClientPassword('test_user', 'test_pass')
        wcs = WCS(auth)
        self.assertTrue(wcs._is_authentication_required)
        self.assertEqual(wcs.timeout_config, (2, 20))
        self.assertEqual(wcs._auth_expires, 0)
        self.assertIsNone(wcs._auth_bearer)
        self.assertEqual(wcs._auth_client_secret, auth)
        self.assertEqual(wcs.url, 'https://wcs.api.semi.technology')
        mock_set_bearer.assert_called_with(
            'wcs',
            'https://auth.wcs.api.semi.technology/auth/realms/SeMI/.well-known/openid-configuration'
        )

        # without DEV
        auth = AuthClientPassword('test_user', 'test_pass')
        wcs = WCS(auth, dev=True)
        self.assertTrue(wcs._is_authentication_required)
        self.assertEqual(wcs.timeout_config, (2, 20))
        self.assertEqual(wcs._auth_expires, 0)
        self.assertIsNone(wcs._auth_bearer)
        self.assertEqual(wcs._auth_client_secret, auth)
        self.assertEqual(wcs.url, 'https://dev.wcs.api.semi.technology')
        mock_set_bearer.assert_called_with(
            'wcs',
            'https://auth.dev.wcs.api.semi.technology/auth/realms/SeMI/.well-known/openid-configuration'
        )

    @patch('weaviate.wcs.crud_wcs.WCS._set_bearer', Mock())
    @patch('weaviate.wcs.crud_wcs.WCS.get_cluster_config')
    def test_is_ready(self, mock_get_cluster_config,):
        """
        Test the `is_ready` method.
        """

        wcs = WCS(AuthClientPassword('test_user', 'test_pass'))

        mock_get_cluster_config.return_value = {'status': {'state': {'percentage' : 99}}}
        self.assertEqual(wcs.is_ready('test_name'), False)
        mock_get_cluster_config.assert_called_with('test_name')

        mock_get_cluster_config.return_value = {'status': {'state': {'percentage' : 100}}}
        self.assertEqual(wcs.is_ready('test_name2'), True)
        mock_get_cluster_config.assert_called_with('test_name2')


    @patch('weaviate.wcs.crud_wcs.WCS._set_bearer', Mock())
    @patch('weaviate.wcs.crud_wcs.WCS.post')
    @patch('weaviate.wcs.crud_wcs.WCS.get_cluster_config')
    def test_create(self, mock_get_cluster_config, mock_post):
        """
        Test the `create` method.
        """

        wcs = WCS(AuthClientPassword('test_user', 'test_pass'))
        wcs._auth_bearer = 'test_auth'
        progress = lambda name, prog = 99: {
            'meta': {'PublicURL': f'{name}.semi.network'},
            'status': {
                'state': {'percentage': prog}
            }
        }

        mock_get_cluster_config.side_effect = progress
        config = {
            'id': 'Test_name',
            'email': 'test@semi.technology',
            'configuration': {
                'tier': 'sandbox', 
                "requiresAuthentication": False
            }
        }

        # invalid calls

        ## error messages
        connection_error_message = 'WCS cluster was not created.'
        unexpected_error_message = 'Creating WCS instance'
        key_error_message = lambda  m: (
            "A module should have a required key: 'name',  and optional keys: 'tag', 'repo' and/or 'inferenceUrl'!"
            f" Given keys: {m.keys()}"
        )
        type_error_message = lambda t: (
            "Wrong type for the `modules` argument. Accepted types are: NoneType, 'str', 'dict' or "
            f"`list` but given: {t}"
        )

        key_type_error_msg = "The type of each value of the module's dict should be 'str'!"
        module_type_msg = "Wrong type for one of the modules. Should be either 'str' or 'dict' but given: "
        config_type_error_msg = "The `config` argument must be either None or of type 'dict', given:"

        # config error
        with self.assertRaises(TypeError) as error:
            wcs.create(config=[{'name': 'TEST!'}])
        check_startswith_error_message(self, error, config_type_error_msg)

        # modules error
        ## no `name` key
        modules = {}
        with self.assertRaises(KeyError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', modules=modules)
        check_error_message(self, error, f'"{key_error_message(modules)}"') # KeyError adds extra quotes

        ## extra key
        modules = {'name': 'Test Name', 'tag': 'Test Tag', 'invalid': 'Test'}
        with self.assertRaises(KeyError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', modules=modules)
        check_error_message(self, error, f'"{key_error_message(modules)}"')# KeyError adds extra quotes

        ## module config type
        with self.assertRaises(TypeError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', modules=12234)
        check_error_message(self, error, type_error_message(int))

        ## module config type when list
        with self.assertRaises(TypeError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', modules=['test1', None])
        check_startswith_error_message(self, error, module_type_msg)

        ## wrong key value type
        with self.assertRaises(TypeError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', modules=[{'name': 123}])
        check_startswith_error_message(self, error, key_type_error_msg)

        # connection error
        mock_post.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type')
        check_error_message(self, error, connection_error_message)
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object={
                'id': 'Test_name',
                'configuration': {
                    'tier': 'test_type',
                    "requiresAuthentication": False,
                    'modules': []
                }
            },
        )

        mock_post.side_effect = None
        mock_post.return_value = Mock(status_code=404)

        # unexpected error
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.create(config=config)
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object=config,
        )


        # valid calls
        mock_post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url')
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object={'id': 'my-url', 'configuration': {'tier': 'sandbox', "requiresAuthentication": False, 'modules': []}},
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        mock_post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url', modules='test')
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object={'id': 'my-url', 'configuration': {'tier': 'sandbox', "requiresAuthentication": False, 'modules': [{'name': 'test'}]}},
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        mock_post.return_value = Mock(status_code=400, text='Cluster already exists!')
        modules = ['test', {'name': 'test2', 'repo': 'test_repo', 'tag': 'TAG', 'inferenceUrl': 'URL'}]
        result = wcs.create(cluster_name='my-url', modules=modules, with_auth=True)
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object={
                'id': 'my-url',
                'configuration': {
                    'tier': 'sandbox',
                    "requiresAuthentication": True,
                    'modules': [{'name': modules[0]}, modules[1]]
                }
            },
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        mock_post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url', modules={'name': 'test', 'tag': 'test_tag'})
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object={
                'id': 'my-url',
                'configuration': {
                    'tier': 'sandbox',
                    "requiresAuthentication": False,
                    'modules': [{'name': 'test', 'tag': 'test_tag'}]
                }
            },
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        post_return = Mock(status_code=202)
        post_return.json.return_value = {'id': 'test_id'}
        mock_post.return_value = post_return
        result = wcs.create(config=config, wait_for_completion=False)
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object=config,
        )
        self.assertEqual(result, 'https://test_id.semi.network')

        mock_get_cluster_config.reset_mock()
        mock_get_cluster_config.side_effect = lambda x: progress('weaviate', 100) if mock_get_cluster_config.call_count == 2 else progress('weaviate')
        mock_post.return_value = Mock(status_code=202)
        result = wcs.create(cluster_name='weaviate', wait_for_completion=True)
        mock_post.assert_called_with(
            path='/clusters',
            weaviate_object={
                'id': 'weaviate',
                'configuration': {
                    'tier': 'sandbox',
                    "requiresAuthentication": False,
                    'modules': []
                }
            },
        )
        self.assertEqual(result, 'https://weaviate.semi.network')

    @patch('weaviate.wcs.crud_wcs.WCS._set_bearer', Mock())
    @patch('weaviate.wcs.crud_wcs.WCS.get')
    def test_get_clusters(self, mock_get):
        """
        Test the `get_clusters` method.
        """


        wcs = WCS(AuthClientPassword('test@semi.technology', 'testPassoword'))
        wcs._auth_bearer = 'test_bearer'

        # invalid calls

        ## error messages
        connection_error_message = 'WCS clusters were not fetched.'
        unexpected_error_message = 'Checking WCS instance'

        # connection error
        mock_get.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.get_clusters()
        check_error_message(self, error, connection_error_message)
        mock_get.assert_called_with(
            path='/clusters/list',
            params={
                'email': 'test@semi.technology'
            }
        )

        # unexpected error
        mock_get.side_effect = None
        mock_get.return_value = Mock(status_code=400)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.get_clusters()
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_get.assert_called_with(
            path='/clusters/list',
            params={
                'email': 'test@semi.technology'
            }
        )

        # valid calls
        return_mock = Mock(status_code=200)
        return_mock.json.return_value = {'clusterIDs': 'test!'}
        mock_get.return_value = return_mock
        result = wcs.get_clusters()
        self.assertEqual(result, 'test!')
        mock_get.assert_called_with(
            path='/clusters/list',
            params={
                'email': 'test@semi.technology'
            }
        )

    @patch('weaviate.wcs.crud_wcs.WCS._set_bearer', Mock())
    @patch('weaviate.wcs.crud_wcs.WCS.get')
    def test_get_cluster_config(self, mock_get):
        """
        Test the `get_cluster_config` method.
        """

        wcs = WCS(AuthClientPassword('test_secret_username', 'test_secret_password'))
        wcs._auth_bearer = 'test_bearer'

        # invalid calls

        ## error messages
        connection_error_message = 'WCS cluster info was not fetched.'
        unexpected_error_message = 'Checking WCS instance'

        ## connection error
        mock_get.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.get_cluster_config('test_name')
        check_error_message(self, error, connection_error_message)
        mock_get.assert_called_with(
            path='/clusters/test_name',
        )

        ## unexpected error
        mock_get.side_effect = None
        mock_get.return_value = Mock(status_code=400)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.get_cluster_config('test_name')
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_get.assert_called_with(
            path='/clusters/test_name',
        )

        # valid calls
        return_mock = Mock(status_code=200)
        return_mock.json.return_value = {'clusterIDs': 'test!'}
        mock_get.return_value = return_mock
        result = wcs.get_cluster_config('test_name')
        self.assertEqual(result, {'clusterIDs': 'test!'})
        mock_get.assert_called_with(
            path='/clusters/test_name',
        )

        return_mock = Mock(status_code=404)
        return_mock.json.return_value = {'clusterIDs': 'test!'}
        mock_get.return_value = return_mock
        result = wcs.get_cluster_config('test_name')
        self.assertEqual(result, {})
        mock_get.assert_called_with(
            path='/clusters/test_name',
        )

    @patch('weaviate.wcs.crud_wcs.WCS._set_bearer', Mock())
    @patch('weaviate.wcs.crud_wcs.WCS.delete')
    def test_delete(self, mock_delete):
        """
        Test the `delete` method.
        """

        wcs = WCS(AuthClientPassword('test_secret_username', 'test_password'))
        wcs._auth_bearer = 'test_bearer'

        # invalid calls

        ## error messages
        connection_error_message = 'WCS cluster was not deleted.'
        unexpected_error_message = 'Deleting WCS instance'

        ## connection error
        mock_delete.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.delete_cluster('test_name')
        check_error_message(self, error, connection_error_message)
        mock_delete.assert_called_with(
            path='/clusters/test_name',
        )

        ## unexpected error
        mock_delete.side_effect = None
        mock_delete.return_value = Mock(status_code=400)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.delete_cluster('test_name')
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_delete.assert_called_with(
            path='/clusters/test_name',
        )

        # valid calls
        mock_delete.return_value = Mock(status_code=200)
        self.assertIsNone(wcs.delete_cluster('test_name'))
        mock_delete.assert_called_with(
            path='/clusters/test_name',
        )

        mock_delete.return_value = Mock(status_code=404)
        self.assertIsNone(wcs.delete_cluster('test_name'))
        mock_delete.assert_called_with(
            path='/clusters/test_name',
        )

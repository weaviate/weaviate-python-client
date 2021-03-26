import unittest
from unittest.mock import patch, Mock
import json
import requests
from requests import RequestException
from weaviate import AuthClientPassword, AuthClientCredentials
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.tools import WCS
from test.util import check_error_message, check_startswith_error_message


class TestWCS(unittest.TestCase):

    @patch('weaviate.tools.wcs.WCS._set_bearer')
    def test___init__(self, mock_set_bearer):
        """
        Test the `__init__` method.
        """
        # invalid calls
        ## error messages
        login_error_message = "No login credentials provided."

        with self.assertRaises(ValueError) as error:
            WCS(None)
        check_error_message(self, error, login_error_message)
        mock_set_bearer.assert_not_called()

        # valid calls
        # without DEV
        auth = AuthClientPassword('test_user', 'test_pass')
        wcs = WCS(auth)
        self.assertTrue(wcs.is_authentication_required)
        self.assertEqual(wcs.timeout_config, (2, 20))
        self.assertEqual(wcs.auth_expires, 0)
        self.assertEqual(wcs.auth_bearer, 0)
        self.assertEqual(wcs.auth_client_secret, auth)
        self.assertEqual(wcs.url, 'https://wcs.api.semi.technology/v1/clusters')
        mock_set_bearer.assert_called_with(
            'wcs',
            'https://auth.wcs.api.semi.technology/auth/realms/SeMI/.well-known/openid-configuration'
        )

        # without DEV
        auth = AuthClientPassword('test_user', 'test_pass')
        wcs = WCS(auth, dev=True)
        self.assertTrue(wcs.is_authentication_required)
        self.assertEqual(wcs.timeout_config, (2, 20))
        self.assertEqual(wcs.auth_expires, 0)
        self.assertEqual(wcs.auth_bearer, 0)
        self.assertEqual(wcs.auth_client_secret, auth)
        self.assertEqual(wcs.url, 'https://dev.wcs.api.semi.technology/v1/clusters')
        mock_set_bearer.assert_called_with(
            'wcs',
            'https://auth.dev.wcs.api.semi.technology/auth/realms/SeMI/.well-known/openid-configuration'
        )

    @patch('weaviate.tools.wcs.WCS._set_bearer')
    @patch('weaviate.tools.wcs.WCS.get_cluster_config')
    def test_is_ready(self, mock_get_cluster_config, mock_set_bearer):
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


    @patch('weaviate.tools.wcs.requests')
    @patch('weaviate.tools.wcs.WCS._set_bearer')
    @patch('weaviate.tools.wcs.WCS.get_cluster_config')
    def test_create(self, mock_get_cluster_config, mock_set_bearer, mock_requests):
        """
        Test the `create` method.
        """

        wcs = WCS(AuthClientPassword('test_user', 'test_pass'), dev=True)
        wcs.auth_bearer = 'test_auth'
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
        connection_error_message = 'Test! Connection error, WCS cluster was not created.'
        unexpected_error_message = 'Creating WCS instance'
        key_error_message = "`module` should have a required 'name' key and an optional 'tag' key!"
        type_error_message = 'Wrong type for `module`, accepted types are str, dict and None!'

        # key error
        with self.assertRaises(KeyError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', module={})
        check_error_message(self, error, f'"{key_error_message}"') # KeyError adds extra quotes

        with self.assertRaises(KeyError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', module={'name': 'Test Name', 'tag': 'Test Tag', 'invalid': 'Test'})
        check_error_message(self, error, f'"{key_error_message}"')# KeyError adds extra quotes

        # type error
        with self.assertRaises(TypeError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type', module=12234)
        check_error_message(self, error, type_error_message)

        # connection error
        mock_requests.post.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.create(cluster_name='Test_name', cluster_type='test_type')
        check_error_message(self, error, connection_error_message)
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'Test_name', 'configuration': {'tier': 'test_type', 'modules': []}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )

        mock_requests.post.side_effect = None
        mock_requests.post.return_value = Mock(status_code=404)

        # unexpected error
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.create(config=config)
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps(config).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )

        # valid calls
        mock_requests.post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url')
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'my-url', 'configuration': {'tier': 'sandbox', 'modules': []}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        mock_requests.post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url', module='test')
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'my-url', 'configuration': {'tier': 'sandbox', 'modules': [{'name': 'test'}]}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        mock_requests.post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url', module={'name': 'test', 'tag': 'test_tag'})
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'my-url', 'configuration': {'tier': 'sandbox', 'modules': [{'name': 'test', 'tag': 'test_tag'}]}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        post_return = Mock(status_code=202)
        post_return.json.return_value = {'id': 'test_id'}
        mock_requests.post.return_value = post_return
        result = wcs.create(config=config, wait_for_completion=False)
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps(config).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://test_id.semi.network')

        mock_get_cluster_config.reset_mock()
        mock_get_cluster_config.side_effect = lambda x: progress('weaviate', 100) if mock_get_cluster_config.call_count == 2 else progress('weaviate')
        mock_requests.post.return_value = Mock(status_code=202)
        result = wcs.create(cluster_name='weaviate', wait_for_completion=True)
        mock_requests.post.assert_called_with(
            url='https://dev.wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'weaviate', 'configuration': {'tier': 'sandbox', 'modules': []}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://weaviate.semi.network')

        # for PROD
        wcs = WCS(AuthClientPassword('test_user', 'test_pass'), dev=False)
        wcs.auth_bearer = 'test_auth'

        mock_get_cluster_config.side_effect = progress

        mock_requests.post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url')
        mock_requests.post.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'my-url', 'configuration': {'tier': 'sandbox'}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://my-url.semi.network')

        mock_requests.post.return_value = Mock(status_code=400, text='Cluster already exists!')
        result = wcs.create(cluster_name='my-url', module='test')
        mock_requests.post.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters',
            data=json.dumps({'id': 'my-url', 'configuration': {'tier': 'sandbox'}}).encode("utf-8"),
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_auth'},
            timeout=(2, 20)
        )
        self.assertEqual(result, 'https://my-url.semi.network')

    @patch('weaviate.tools.wcs.WCS._set_bearer')
    @patch('weaviate.tools.wcs.requests')
    def test_get_clusters(self, mock_requests, mock_set_bearer):
        """
        Test the `get_clusters` method.
        """

        wcs = WCS(AuthClientCredentials('test_secret_token'))
        wcs.auth_bearer = 'test_bearer'

        # invalid calls

        ## error messages
        connection_error_message = 'Test! Connection error, WCS clusters were not fetched.'
        unexpected_error_message = 'Checking WCS instance'

        # connection error
        mock_requests.get.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.get_clusters('test@semi.technology')
        check_startswith_error_message(self, error, connection_error_message)
        mock_requests.get.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/list',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
            params={
                'email': 'test@semi.technology'
            }
        )

        # unexpected error
        mock_requests.get.side_effect = None
        mock_requests.get.return_value = Mock(status_code=400)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.get_clusters('test@semi.technology')
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_requests.get.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/list',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
            params={
                'email': 'test@semi.technology'
            }
        )

        # valid calls
        return_mock = Mock(status_code=200)
        return_mock.json.return_value = {'clusterIDs': 'test!'}
        mock_requests.get.return_value = return_mock
        result = wcs.get_clusters('test@semi.technology')
        self.assertEqual(result, 'test!')
        mock_requests.get.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/list',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
            params={
                'email': 'test@semi.technology'
            }
        )

    @patch('weaviate.tools.wcs.WCS._set_bearer')
    @patch('weaviate.tools.wcs.requests')
    def test_get_cluster_config(self, mock_requests, mock_set_bearer):
        """
        Test the `get_cluster_config` method.
        """

        wcs = WCS(AuthClientCredentials('test_secret_token'))
        wcs.auth_bearer = 'test_bearer'

        # invalid calls

        ## error messages
        connection_error_message = 'Test! Connection error, WCS cluster info was not fetched.'
        unexpected_error_message = 'Checking WCS instance'

        ## connection error
        mock_requests.get.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.get_cluster_config('test_name')
        check_startswith_error_message(self, error, connection_error_message)
        mock_requests.get.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/test_name',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
        )

        ## unexpected error
        mock_requests.get.side_effect = None
        mock_requests.get.return_value = Mock(status_code=400)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.get_cluster_config('test_name')
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_requests.get.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/test_name',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
        )

        # valid calls
        return_mock = Mock(status_code=200)
        return_mock.json.return_value = {'clusterIDs': 'test!'}
        mock_requests.get.return_value = return_mock
        result = wcs.get_cluster_config('test_name')
        self.assertEqual(result, {'clusterIDs': 'test!'})
        mock_requests.get.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/test_name',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
        )

    @patch('weaviate.tools.wcs.WCS._set_bearer')
    @patch('weaviate.tools.wcs.requests')
    def test_delete(self, mock_requests, mock_set_bearer):
        """
        Test the `delete` method.
        """

        wcs = WCS(AuthClientCredentials('test_secret_token'))
        wcs.auth_bearer = 'test_bearer'

        # invalid calls

        ## error messages
        connection_error_message = 'Test! Connection error, WCS cluster was not deleted.'
        unexpected_error_message = 'Deleting WCS instance'

        ## connection error
        mock_requests.delete.side_effect = RequestsConnectionError('Test!')
        with self.assertRaises(RequestsConnectionError) as error:
            wcs.delete('test_name')
        check_startswith_error_message(self, error, connection_error_message)
        mock_requests.delete.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/test_name',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
        )

        ## unexpected error
        mock_requests.delete.side_effect = None
        mock_requests.delete.return_value = Mock(status_code=400)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            wcs.delete('test_name')
        check_startswith_error_message(self, error, unexpected_error_message)
        mock_requests.delete.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/test_name',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
        )

        # valid calls
        mock_requests.delete.return_value = Mock(status_code=200)
        self.assertIsNone(wcs.delete('test_name'))
        mock_requests.delete.assert_called_with(
            url='https://wcs.api.semi.technology/v1/clusters/test_name',
            headers={"content-type": "application/json", 'Authorization': 'Bearer test_bearer'},
            timeout=(2, 20),
        )

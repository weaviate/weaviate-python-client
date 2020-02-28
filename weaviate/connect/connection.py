import requests
import time
import urllib
from weaviate.connect import *
from weaviate.exceptions import *
from weaviate.connect.constants import *
from requests.exceptions import ConnectionError

WEAVIATE_REST_API_VERSION_PATH = "/v1"

class Connection:

    def __init__(self, url, auth_client_secret=None, timeout_config=None):
        """
        :param url:
        :param auth_client_secret:
        :param timeout_config: Set the timeout config as a tuple of (retries, time out seconds)
        :type timeout_config: tuple of int
        """
        self.url = url+WEAVIATE_REST_API_VERSION_PATH  # e.g. http://localhost:80/v1
        if timeout_config is None:
            self.timeout_config = (2, 20)
        else:
            self.timeout_config = timeout_config

        self.auth_expires = 0  # unix time when auth expires
        self.auth_bearer = 0
        self.auth_client_secret = auth_client_secret

        self.is_authentication_required = False
        try:
            request = requests.get(self.url + "/.well-known/openid-configuration",
                                   headers={"content-type": "application/json"}, timeout=(30, 45))
        except Exception as error:
            pass
        else:
            if request.status_code == 200:
                self.is_authentication_required = True
                self._refresh_authentication()

    # Requests a new bearer
    def _refresh_authentication(self):
        if (self.auth_expires - 2) < get_epoch_time():  # -2 for some lagtime
            self._auth_get_bearer()


    def _auth_get_bearer(self):

        # collect data for the request
        try:
            request = requests.get(self.url + "/.well-known/openid-configuration", headers={"content-type": "application/json"}, timeout=(30, 45))
        except urllib.error.HTTPError as error:
            raise AuthenticationFailedException("Cant connect to weaviate")
        if request.status_code != 200:
            raise AuthenticationFailedException("Cant authenticate http status not ok")

        # Set the client ID
        client_id = request.json()['clientId']

        # request additional information
        try:
            request_third_part = requests.get(request.json()['href'], headers={"content-type": "application/json"}, timeout=(30, 45))
        except urllib.error.HTTPError as error:
            raise AuthenticationFailedException(
                "Can't connect to the third party authentication service. Validate that it's running")
        if request_third_part.status_code != 200:
            raise AuthenticationFailedException(
                "Status not OK in connection to the third party authentication service")

        # Validate third part auth info
        if 'client_credentials' not in request_third_part.json()['grant_types_supported']:
            raise AuthenticationFailedException(
                "The grant_types supported by the thirdparty authentication service are insufficient. Please add 'client_credentials'")

        request_body = self.auth_client_secret.get_credentials()
        request_body["client_id"] = client_id

        # try the request
        try:
            request = requests.post(request_third_part.json()['token_endpoint'], request_body, timeout=(30, 45))
        except urllib.error.HTTPError:
            raise AuthenticationFailedException(
                "Unable to get a OAuth token from server. Are the credentials and URLs correct?")

        # sleep to process
        time.sleep(0.125)

        if request.status_code == 401:
            raise AuthenticationFailedException(
                "Authtentication access denied are the credentials correct?"
            )

        self.auth_bearer = request.json()['access_token']
        self.auth_expires = int(get_epoch_time() + request.json()['expires_in'] - 2)

    def _get_request_header(self):
        """Returns the correct headers for a request"""

        header = {"content-type": "application/json"}

        if self.is_authentication_required:
            self._refresh_authentication()
            header["Authorization"] = "Bearer " + self.auth_bearer

        return header

    def run_rest(self, path, rest_method, weaviate_object=None, params=None):
        """ Make a request to weaviate

        :param path: must be a valid weaviate sub-path e.g. /meta or /things without version.
        :type path: str
        :param rest_method: is defined through a constant given in the package e.g. REST_METHOD_GET.
        :type rest_method: enum constant
        :param weaviate_object: if set this object is used as payload.
        :type weaviate_object: dict
        :param params: additional request prameter.
        :type params: dict
        :return: the response if request was successful.
        :raises:
            ConnectionError: If weaviate could not be reached.
        """
        if params is None:
            params = {}
        request_url = self.url+path

        try:
            if rest_method == REST_METHOD_GET:
                response = requests.get(url=request_url,
                                        headers=self._get_request_header(), timeout=self.timeout_config, params=params)
            elif rest_method == REST_METHOD_PUT:
                response = requests.put(url=request_url, json=weaviate_object,
                                        headers=self._get_request_header(), timeout=self.timeout_config)
            elif rest_method == REST_METHOD_POST:
                response = requests.post(url=request_url, json=weaviate_object,
                                         headers=self._get_request_header(), timeout=self.timeout_config)
            elif rest_method == REST_METHOD_PATCH:
                response = requests.patch(url=request_url, json=weaviate_object,
                                          headers=self._get_request_header(), timeout=self.timeout_config)
            elif rest_method == REST_METHOD_DELETE:
                response = requests.delete(url=request_url, json=weaviate_object,
                                          headers=self._get_request_header(), timeout=self.timeout_config)
            else:
                print("Not yet implemented rest method called")
                response = None
        except ConnectionError:
            raise

        else:
            return response

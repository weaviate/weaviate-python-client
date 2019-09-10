import requests
import time
import urllib
from weaviate.connect import *


WEAVIATE_REST_API_VERSION_PATH = "/v1"

class Connection:

    def __init__(self, url, auth_client_secret=""):
        self.url = url+WEAVIATE_REST_API_VERSION_PATH  # e.g. http://localhost:80/v1
        self.auth_expires = 0  # unix time when auth expires
        self.auth_bearer = 0
        self.auth_client_secret = auth_client_secret

        self.is_authentication_required = False
        try:
            request = requests.get(self.url + "/.well-known/openid-configuration",
                                   headers={"content-type": "application/json"}, timeout=(30, 45))
        except urllib.error.HTTPError as error:
            pass
        else:
            if request.status_code == 200:
                self.is_authentication_required = True
                self.__refresh_authentication()

    # Requests a new bearer
    def __refresh_authentication(self):
        if (self.auth_expires - 2) < get_epoch_time():  # -2 for some lagtime
            self.__auth_get_bearer()


    def __auth_get_bearer(self):

        # collect data for the request
        try:
            request = requests.get(self.url + "/.well-known/openid-configuration", headers={"content-type": "application/json"}, timeout=(30, 45))
        except urllib.error.HTTPError as error:
            raise Errors.AuthenticationFailedException("Cant connect to weaviate")
        if request.status_code != 200:
            raise Errors.AuthenticationFailedException("Cant authenticate http status not ok")

        # Set the client ID
        client_id = request.json()['clientId']

        # request additional information
        try:
            request_third_part = requests.get(request.json()['href'], headers={"content-type": "application/json"}, timeout=(30, 45))
        except urllib.error.HTTPError as error:
            raise Errors.AuthenticationFailedException(
                "Can't connect to the third party authentication service. Validate that it's running")
        if request_third_part.status_code != 200:
            raise Errors.AuthenticationFailedException(
                "Status not OK in connection to the third party authentication service")

        # Validate third part auth info
        if 'client_credentials' not in request_third_part.json()['grant_types_supported']:
            raise Errors.AuthenticationFailedException(
                "The grant_types supported by the thirdparty authentication service are insufficient. Please add 'client_credentials'")

        # Set the body
        request_body = {
            "client_id": client_id,
            "grant_type": 'client_credentials',
            "client_secret": self.auth_client_secret
        }

        # try the request
        try:
            request = requests.post(request_third_part.json()['token_endpoint'], request_body, timeout=(30, 45))
        except urllib.error.HTTPError as error:
            raise Errors.AuthenticationFailedException(
                "Unable to get a OAuth token from server. Are the credentials and URLs correct?")

        # sleep to process
        time.sleep(0.125)

        self.auth_bearer = request.json()['access_token']
        self.auth_expires = int(get_epoch_time() + request.json()['expires_in'] - 2)

    def __get_request_header(self):
        """Returns the correct headers for a request"""

        header = {"content-type": "application/json"}

        if self.is_authentication_required:
            self.__refresh_authentication()
            header["Authorization"] = "Bearer " + self.auth_bearer

        return header

    # Make a request to weaviate
    # path must be a valid weaviate sub-path e.g. /meta or /things
    # The weaviate_object must must have the form of a dict
    # The rest_method is defined through a constant given in the package
    # The retries define how often the request is retried in case of exceptions, until it ultimately fails
    # Returns the response of the request
    def run_rest(self, path, rest_method, weaviate_object=None, retries=3):

        request_url = self.url+path
        try:
            if rest_method == REST_METHOD_GET:
                response = requests.get(url=request_url,
                                        headers=self.__get_request_header(), timeout=(2, 20))
            elif rest_method == REST_METHOD_PUT:
                response = requests.put(url=request_url, json=weaviate_object,
                                        headers=self.__get_request_header(), timeout=(2, 20))
            elif rest_method == REST_METHOD_POST:
                response = requests.post(url=request_url, json=weaviate_object,
                                         headers=self.__get_request_header(), timeout=(2, 20))
            else:
                print("Not yet implemented rest method called")
                response = None
        except ConnectionError as conn_err:
            if retries > 0:
                time.sleep(0.125)
                self.run_rest(path, weaviate_object, rest_method, retries - 1)
                return
            else:
                raise ConnectionError
        else:
            return response

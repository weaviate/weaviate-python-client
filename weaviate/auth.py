from weaviate.connect.credentials import AuthCredentials
import base64
import copy

class AuthClientCredentials(AuthCredentials):
    """ Using a client secret for authentication.
        In case of grand type client credentials.
    """

    def __init__(self, client_secret):
        """ Using a client secret for authentication.
            In case of grand type client credentials.
        :param client_secret: the access token
        :type client_secret: str
        """
        AuthCredentials.__init__(self)
        self._credentials_body["grant_type"] = "client_credentials"
        self.cs = base64.b64encode(client_secret.encode('ascii')).decode('ascii')

    def get_credentials(self):
        return_body = copy.deepcopy(self._credentials_body)
        return_body["client_secret"] = base64.b64decode(self.cs.encode('ascii')).decode('ascii')
        return return_body


class AuthClientPassword(AuthCredentials):
    """ Using username and password for authentication
        In case of grand type password
    """

    def __init__(self, username, password):
        """ Using username and password for authentication
            In case of grand type password
        :param username: User
        :type username: str
        :param password: Password
        :type password: str
        """
        AuthCredentials.__init__(self)
        self._credentials_body["grant_type"] = "password"
        self._credentials_body["username"] = username
        self.pw = base64.b64encode(password.encode('ascii')).decode('ascii')

    def get_credentials(self):
        return_body = copy.deepcopy(self._credentials_body)
        return_body["password"] = base64.b64decode(self.pw.encode('ascii')).decode('ascii')
        return return_body


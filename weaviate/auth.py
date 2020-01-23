from weaviate.connect.credentials import AuthCredentials

# TODO docu
# TODO make secure???

class AuthClientCredentials(AuthCredentials):

    def __init__(self, client_secret):
        AuthCredentials.__init__(self)
        self._credentials_body["grant_type"] = "client_credentials"
        self._credentials_body["client_secret"] = client_secret


class AuthClientPassword(AuthCredentials):

    def __init__(self, username, password):
        AuthCredentials.__init__(self)
        self._credentials_body["grant_type"] = "password"
        self._credentials_body["username"] = username
        self._credentials_body["password"] = password

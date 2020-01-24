class AuthCredentials:
    """ Base class for getting the grand type and credentials
    """

    def __init__(self):
        self._credentials_body = {}

    def get_credentials(self):
        """
        
        :return: credentials and grand type in form of a dict
        """
        return self._credentials_body
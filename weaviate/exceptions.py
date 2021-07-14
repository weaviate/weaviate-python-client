"""
Weaviate Exceptions.
"""
# Import requests ConnectionError as weaviate.ConnectionError to overwrite buildins connection error
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests import Response


class UnexpectedStatusCodeException(Exception):
    """
    Is raised in case the status code returned from Weaviate is
    not handled in the client implementation and suggests an error.
    """
    def __init__(self, message: str, response: Response):
        """
        Is raised in case the status code returned from Weaviate is
        not handled in the client implementation and suggests an error.

        Custom code can act on the attributes:
        - status_code
        - json

        Parameters
        ----------
        message: str
            An error message specific to the context, in which the error occurred.
        response: requests.Response
            The request response of which the status code was unexpected.
        """

        super().__init__()

        # Set error message

        try:
            body = response.json()
        except:
            body = None

        self.message = message
        self.status_code = response.status_code
        self.json = body

    def __str__(self):
        code = str(self.status_code)
        body = str(self.json)
        return f"{self.message}! Unexpected status code: {code}, with response body: {body}"


class ObjectAlreadyExistsException(Exception):
    """
    Object Already Exists Exception.
    """


class AuthenticationFailedException(Exception):
    """
    Authentication Failed Exception.
    """

class SchemaValidationException(Exception):
    """
    Schema Validation Exception.
    """

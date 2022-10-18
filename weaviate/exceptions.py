"""
Weaviate Exceptions.
"""
# Import requests ConnectionError as weaviate.ConnectionError to overwrite buildins connection error
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests import Response

class WeaviateBaseError(Exception):
    """
    Weaviate base exception that all Weaviate exceptions should inherit from.
    This error can be used to catch any Weaviate exceptions.
    """

    def __init__(self, message: str = ''):
        """
        Weaviate base exception initializer.
        Parameters
        ----------
        message: str, optional
            An error message specific to the context in which the error occurred.
        """

        self.message = message
        super().__init__(message)


class UnexpectedStatusCodeException(WeaviateBaseError):
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


        # Set error message

        try:
            body = response.json()
        except:
            body = None

        super().__init__(
            message
            + f"! Unexpected status code: {response.status_code}, with response body: {body}"
        )


class ObjectAlreadyExistsException(WeaviateBaseError):
    """
    Object Already Exists Exception.
    """


class AuthenticationFailedException(WeaviateBaseError):
    """
    Authentication Failed Exception.
    """


class SchemaValidationException(WeaviateBaseError):
    """
    Schema Validation Exception.
    """

class BackupFailedException(WeaviateBaseError):
    """
    Backup Failed Exception.
    """

class EmptyResponseException(WeaviateBaseError):
    """
    Occurs when an HTTP request unexpectedly returns an empty response
    """

"""
Weaviate Exceptions.
"""

from requests import Response, exceptions

ERROR_CODE_EXPLANATION = {
    413: """Payload Too Large. Try to decrease the batch size or increase the maximum request size on your weaviate
         server."""
}


class WeaviateBaseError(Exception):
    """
    Weaviate base exception that all Weaviate exceptions should inherit from.
    This error can be used to catch any Weaviate exceptions.
    """

    def __init__(self, message: str = ""):
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
        self._status_code: int = response.status_code
        # Set error message

        try:
            body = response.json()
        except exceptions.JSONDecodeError:
            body = None

        msg = (
            message
            + f"! Unexpected status code: {response.status_code}, with response body: {body}."
        )
        if response.status_code in ERROR_CODE_EXPLANATION:
            msg += " " + ERROR_CODE_EXPLANATION[response.status_code]

        super().__init__(msg)

    @property
    def status_code(self) -> int:
        return self._status_code


class ResponseCannotBeDecodedException(WeaviateBaseError):
    def __init__(self, location: str, response: Response):
        """Raised when a weaviate response cannot be decoded to json

        Parameters
        ----------
        location: str
            From which code path the exception was raised.
        response: requests.Response
            The request response of which the status code was unexpected.
        """
        msg = f"Cannot decode response from weaviate {response} with content {response.text} for request from {location}"
        super().__init__(msg)
        self._status_code: int = response.status_code

    @property
    def status_code(self) -> int:
        return self._status_code


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


class MissingScopeException(WeaviateBaseError):
    """Scope was not provided with client credential flow."""


class AdditionalPropertiesException(WeaviateBaseError):
    """Additional properties were provided multiple times."""

    def __init__(self, additional_dict: str, additional_dataclass: str):
        msg = f"""
        Cannot add AdditionalProperties class together with string-additional properties. Did you call
            .with_additional() multiple times?.
             Current additional properties already present:
                - strings: {additional_dict}
                - AdditionalProperties class: {additional_dataclass}
        """
        super().__init__(msg)


class WeaviateStartUpError(WeaviateBaseError):
    """Is raised if weaviate does not start up in time."""


class WeaviateEmbeddedInvalidVersion(WeaviateBaseError):
    """Invalid version provided to Weaviate embedded."""

    def __init__(self, url: str):
        msg = f"""Invalid version provided to Weaviate embedded. It must be either:
        - a url to a tar.gz file that contains a Weaviate binary
        - a version number, eg "1.18.2"
        - the string "latest" to download the latest non-beta version

        Url provided was: {url}.
        """
        super().__init__(msg)

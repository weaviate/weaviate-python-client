"""
Weaviate Exceptions.
"""

from json.decoder import JSONDecodeError
from typing import Tuple, Union

import httpx
from grpc.aio import AioRpcError  # type: ignore

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

        Arguments:
            `message`:
                An error message specific to the context in which the error occurred.
        """

        self.message = message
        super().__init__(message)


class UnexpectedStatusCodeError(WeaviateBaseError):
    """
    Is raised in case the status code returned from Weaviate is
    not handled in the client implementation and suggests an error.
    """

    def __init__(self, message: str, response: Union[httpx.Response, AioRpcError]):
        """
        Is raised in case the status code returned from Weaviate is
        not handled in the client implementation and suggests an error.

        Custom code can act on the attributes:
        - status_code
        - json

        Arguments:
            `message`:
                An error message specific to the context, in which the error occurred.
            `response`:
                The request response of which the status code was unexpected.
        """
        if isinstance(response, httpx.Response):
            self._status_code: int = response.status_code
            # Set error message

            try:
                body = response.json()
            except (httpx.DecodingError, JSONDecodeError):
                body = None

            msg = (
                message
                + f"! Unexpected status code: {response.status_code}, with response body: {body}."
            )
            if response.status_code in ERROR_CODE_EXPLANATION:
                msg += " " + ERROR_CODE_EXPLANATION[response.status_code]
        elif isinstance(response, AioRpcError):
            self._status_code = int(response.code().value[0])
            msg = (
                message
                + f"! Unexpected status code: {response.code().value[1]}, with response body: {response.details()}."
            )
        super().__init__(msg)

    @property
    def status_code(self) -> int:
        return self._status_code


UnexpectedStatusCodeException = UnexpectedStatusCodeError


class ResponseCannotBeDecodedError(WeaviateBaseError):
    def __init__(self, location: str, response: httpx.Response):
        """Raised when a weaviate response cannot be decoded to json

        Arguments:
            `location`:
                From which code path the exception was raised.
            `response`:
                The request response of which the status code was unexpected.
        """
        msg = f"Cannot decode response from weaviate {response} with content '{response.text}' for request from {location}"
        super().__init__(msg)
        self._status_code: int = response.status_code

    @property
    def status_code(self) -> int:
        return self._status_code


ResponseCannotBeDecodedException = ResponseCannotBeDecodedError


class ObjectAlreadyExistsError(WeaviateBaseError):
    """
    Object Already Exists Exception.
    """


ObjectAlreadyExistsException = ObjectAlreadyExistsError


class AuthenticationFailedError(WeaviateBaseError):
    """
    Authentication Failed Exception.
    """


AuthenticationFailedException = AuthenticationFailedError


class SchemaValidationError(WeaviateBaseError):
    """
    Schema Validation Exception.
    """


SchemaValidationException = SchemaValidationError


class BackupFailedError(WeaviateBaseError):
    """
    Backup Failed Exception.
    """


BackupFailedException = BackupFailedError


class BackupCanceledError(WeaviateBaseError):
    """
    Backup canceled Exception.
    """


class EmptyResponseError(WeaviateBaseError):
    """
    Occurs when an HTTP request unexpectedly returns an empty response
    """


EmptyResponseException = EmptyResponseError


class MissingScopeError(WeaviateBaseError):
    """Scope was not provided with client credential flow."""


MissingScopeException = MissingScopeError


class AdditionalPropertiesError(WeaviateBaseError):
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


AdditionalPropertiesException = AdditionalPropertiesError


class InvalidDataModelError(WeaviateBaseError):
    """Is raised when the user provides a generic that is not supported"""

    def __init__(self, type_: str) -> None:
        msg = f"""{type_} can only be a dict type, e.g. Dict[str, Any], or a class that inherits from TypedDict"""
        super().__init__(msg)


InvalidDataModelException = InvalidDataModelError


class WeaviateStartUpError(WeaviateBaseError):
    """Is raised if weaviate is not available on the given url+port."""


class WeaviateEmbeddedInvalidVersionError(WeaviateBaseError):
    """Invalid version provided to Weaviate embedded."""

    def __init__(self, url: str):
        msg = f"""Invalid version provided to Weaviate embedded. It must be either:
        - a url to a tar.gz file that contains a Weaviate binary
        - a version number, eg "1.18.2"
        - the string "latest" to download the latest non-beta version

        Url provided was: {url}.
        """
        super().__init__(msg)


WeaviateEmbeddedInvalidVersionException = WeaviateEmbeddedInvalidVersionError


class WeaviateInvalidInputError(WeaviateBaseError):
    """Is raised if the input to a function is invalid."""

    def __init__(self, message: str):
        msg = f"""Invalid input provided: {message}."""
        super().__init__(msg)
        self.message = message


WeaviateInvalidInputException = WeaviateInvalidInputError


class WeaviateQueryError(WeaviateBaseError):
    """Is raised if a query (either gRPC or GraphQL) to Weaviate fails in any way."""

    def __init__(self, message: str, protocol_type: str):
        msg = f"""Query call with protocol {protocol_type} failed with message {message}."""
        super().__init__(msg)
        self.message = message


WeaviateQueryException = WeaviateQueryError


class WeaviateBatchError(WeaviateQueryError):
    """Is raised if a gRPC batch query to Weaviate fails in any way."""

    def __init__(self, message: str):
        super().__init__(message, "GRPC batch")
        self.message = message


class WeaviateDeleteManyError(WeaviateQueryError):
    """Is raised if a gRPC delete many request to Weaviate fails in any way."""

    def __init__(self, message: str):
        super().__init__(message, "GRPC delete")
        self.message = message


class WeaviateTenantGetError(WeaviateQueryError):
    """Is raised if a gRPC tenant get request to Weaviate fails in any way."""

    def __init__(self, message: str):
        super().__init__(message, "tenant get")
        self.message = message


class WeaviateAddInvalidPropertyError(WeaviateBaseError):
    """Is raised when adding an invalid new property."""

    def __init__(self, message: str):
        msg = f"""Could not add the property {message}. Only optional properties or properties with default
        value are valid"""
        super().__init__(msg)
        self.message = message


class WeaviateBatchValidationError(WeaviateBaseError):
    """Is raised when a batch validation error occurs."""

    def __init__(self, message: str):
        msg = f"""Batch validation error: {message}"""
        super().__init__(msg)
        self.message = message


class WeaviateInsertInvalidPropertyError(WeaviateBaseError):
    """Is raised when inserting an invalid property."""

    def __init__(self, data: dict):
        msg = f"""It is forbidden to insert `id` or `vector` inside properties: {data}. Only properties defined in your collection's config can be inserted as properties of the object, `id` is totally forbidden as it is reserved and `vector` is forbidden at this level. You should use the `DataObject` class if you wish to insert an object with a custom `vector` whilst inserting its properties."""
        super().__init__(msg)


class WeaviateGRPCUnavailableError(WeaviateBaseError):
    """Is raised when a gRPC-backed query is made with no gRPC connection present."""

    def __init__(
        self, weaviate_version: str = "", grpc_address: Tuple[str, int] = ("not provided", 0)
    ) -> None:
        if grpc_address[0] == "not provided":
            grpc_msg = "Please check the server address and port."
        else:
            grpc_msg = f"Please check that the server address and port ({grpc_address[0]}:{grpc_address[1]}) are correct."
        msg = f"""
Weaviate {weaviate_version} makes use of a high-speed gRPC API as well as a REST API.
Unfortunately, the gRPC health check against Weaviate could not be completed.

This error could be due to one of several reasons:
- The gRPC traffic at the specified port is blocked by a firewall.
- gRPC is not enabled or incorrectly configured on the server or the client.
    - {grpc_msg}
- your connection is unstable or has a high latency. In this case you can:
    - increase init-timeout in `weaviate.connect_to_local(additional_config=wvc.init.AdditionalConfig(timeout=wvc.init.Timeout(init=X)))`
    - disable startup checks by connecting using `skip_init_checks=True`
"""
        super().__init__(msg)


WeaviateGrpcUnavailable = WeaviateGRPCUnavailableError


class WeaviateInsertManyAllFailedError(WeaviateBaseError):
    """Is raised when all objects fail to be inserted."""

    def __init__(self, message: str = "") -> None:
        msg = f"""Every object failed during insertion. {message}"""
        super().__init__(msg)


class WeaviateClosedClientError(WeaviateBaseError):
    """Is raised when a client is closed and a method is called on it."""

    def __init__(self) -> None:
        msg = "The `WeaviateClient` is closed. Run `client.connect()` to (re)connect!"
        super().__init__(msg)


class WeaviateConnectionError(WeaviateBaseError):
    """Is raised when the connection to Weaviate fails."""

    def __init__(self, message: str = "") -> None:
        msg = f"""Connection to Weaviate failed. Details: {message}"""
        super().__init__(msg)


class WeaviateUnsupportedFeatureError(WeaviateBaseError):
    """Is raised when a client method tries to use a new feature with an old Weaviate version."""

    def __init__(self, feature: str, current: str, minimum: str) -> None:
        msg = f"""{feature} is not supported by your connected server's Weaviate version. The current version is {current}, but the feature requires at least version {minimum}."""
        super().__init__(msg)


class WeaviateTimeoutError(WeaviateBaseError):
    """Is raised when a request to Weaviate times out."""

    def __init__(self, message: str = "") -> None:
        msg = f"""The request to Weaviate timed out while awaiting a response. Try adjusting the timeout config for your client. Details: {message}"""
        super().__init__(msg)


class WeaviateRetryError(WeaviateBaseError):
    """Is raised when a request to Weaviate fails and is retried multiple times."""

    def __init__(self, message: str, count: int) -> None:
        msg = f"""The request to Weaviate failed after {count} retries. Details: {message}"""
        super().__init__(msg)


class InsufficientPermissionsError(UnexpectedStatusCodeError):
    """Is raised when a request to Weaviate fails due to insufficient permissions."""

    def __init__(self, res: Union[httpx.Response, AioRpcError]) -> None:
        super().__init__("forbidden", res)


class WeaviateAgentsNotInstalledError(WeaviateBaseError):
    """Error raised when trying to use Weaviate Agents without the required dependencies."""

    def __init__(self) -> None:
        super().__init__(
            'Weaviate Agents (Alpha) functionality requires additional dependencies. Please install them using: "pip install weaviate-client[agents]"'
        )

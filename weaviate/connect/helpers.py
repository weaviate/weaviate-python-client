# DONT MERGE - FOR COMMENTING

"""Helper functions for creating a new WeaviateClient in common scenarios."""
from urllib.parse import urlparse
from typing import Optional, Dict

from weaviate.auth import AuthCredentials
from weaviate.client import WeaviateClient
from weaviate.config import AdditionalConfig
from weaviate.connect.base import ConnectionParams, ProtocolParams
from weaviate.embedded import EmbeddedOptions


def connect_to_wcs(
    cluster_url: str,
    auth_credentials: Optional[AuthCredentials],
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    skip_init_checks: bool = False,
) -> WeaviateClient:
    """
    Connect to your own Weaviate Cloud Service (WCS) instance.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `cluster_url`
            The WCS cluster URL or hostname to connect to. Usually in the form rAnD0mD1g1t5.something.weaviate.cloud
        `auth_credentials`
            The credentials to use for authentication with your WCS instance. This can be an API key, in which case use `weaviate.AuthApiKey`,
            a bearer token, in which case use `weaviate.AuthBearerToken`, a client secret, in which case use `weaviate.AuthClientCredentials`
            or a username and password, in which case use `weaviate.AuthClientPassword`.
        `headers`
            Additional headers to include in the requests, e.g. API keys for third-party Cloud vectorisation.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `skip_init_checks`
            Whether to skip the initialisation checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the cluster with the required parameters set appropriately.

    Examples:
        >>> import weaviate
        >>> client = weaviate.connect_to_wcs(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.AuthApiKey("my-api-key"),
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        ################## With Context Manager #############################
        >>> import weaviate
        >>> with weaviate.connect_to_wcs(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.AuthApiKey("my-api-key"),
        ... ) as client:
        ...     client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    if cluster_url.startswith("http"):
        # Handle the common case of copy/pasting a URL instead of the hostname.
        cluster_url = urlparse(cluster_url).netloc
    grpc_host = f"grpc-{cluster_url}"

    client = WeaviateClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(host=cluster_url, port=443, secure=True),
            grpc=ProtocolParams(host=grpc_host, port=443, secure=True),
        ),
        auth_client_secret=auth_credentials,
        additional_headers=headers,
        additional_config=additional_config,
        skip_init_checks=skip_init_checks,
    )
    client.connect()
    return client


def connect_to_local(
    host: str = "localhost",
    port: int = 8080,
    grpc_port: int = 50051,
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    skip_init_checks: bool = False,
    auth_credentials: Optional[AuthCredentials] = None,
) -> WeaviateClient:
    """
    DWC:
    Connect to a local Weaviate instance deployed using Docker compose with standard port configurations.
    
    DWC:
    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `host`
            The host to use for the underlying REST & GraphQL API calls.
        `port`
            The port to use for the underlying REST & GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorisation.
        `timeout`
            The timeout to use for the underlying HTTP calls. Accepts a tuple of integers, where the first integer
            represents the connect timeout and the second integer represents the read timeout.
        `skip_init_checks`
            Whether to skip the initialisation checks when connecting to Weaviate.
        `auth_credentials`
            The credentials to use for authentication with your instance. This can be an API key, in which case use `weaviate.AuthApiKey`,
            a bearer token, in which case use `weaviate.AuthBearerToken`, a client secret, in which case use `weaviate.AuthClientCredentials`
            or a username and password, in which case use `weaviate.AuthClientPassword`.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the local instance with default parameters set as:

    Examples:
        >>> import weaviate
        >>> client = weaviate.connect_to_local(
        ...     host="localhost",
        ...     port=8080,
        ...     grpc_port=50051,
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        ################## With Context Manager #############################
        >>> import weaviate
        >>> with weaviate.connect_to_local(
        ...     host="localhost",
        ...     port=8080,
        ...     grpc_port=50051,
        ... ) as client:
        ...     client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    client = WeaviateClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(host=host, port=port, secure=False),
            grpc=ProtocolParams(host=host, port=grpc_port, secure=False),
        ),
        additional_headers=headers,
        additional_config=additional_config,
        skip_init_checks=skip_init_checks,
        auth_client_secret=auth_credentials,
    )
    client.connect()
    return client


def connect_to_embedded(
    port: int = 8079,
    grpc_port: int = 50050,
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    version: str = "1.22.3",
) -> WeaviateClient:
    """
    Connect to an embedded Weaviate instance.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `port`
            The port to use for the underlying REST & GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorisation.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `version`
            Weaviate version to be used for the embedded instance.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the embedded instance with the required parameters set appropriately.

    Examples:
        >>> import weaviate
        >>> client = weaviate.connect_to_embedded(
        ...     port=8080,
        ...     grpc_port=50051,
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        ################## With Context Manager #############################
        >>> import weaviate
        >>> with weaviate.connect_to_embedded(
        ...     port=8080,
        ...     grpc_port=50051,
        ... ) as client:
        ...     client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    client = WeaviateClient(
        embedded_options=EmbeddedOptions(
            port=port,
            grpc_port=grpc_port,
            version=version,
        ),
        additional_headers=headers,
        additional_config=additional_config,
    )
    client.connect()
    return client


def connect_to_custom(
    http_host: str,
    http_port: int,
    http_secure: bool,
    grpc_host: str,
    grpc_port: int,
    grpc_secure: bool,
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    auth_credentials: Optional[AuthCredentials] = None,
    skip_init_checks: bool = False,
) -> WeaviateClient:
    """
    Connect to a Weaviate instance with custom connection parameters.

    If this is not sufficient for your customisation needs then instantiate a `weaviate.WeaviateClient` directly.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `http_host`
            The host to use for the underlying REST & GraphQL API calls.
        `http_port`
            The port to use for the underlying REST & GraphQL API calls.
        `http_secure`
            Whether to use https for the underlying REST & GraphQL API calls.
        `grpc_host`
            The host to use for the underlying gRPC API.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `grpc_secure`
            Whether to use a secure channel for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorisation.
        `timeout`
            The timeout to use for the underlying HTTP calls. Accepts a tuple of integers, where the first integer
            represents the connect timeout and the second integer represents the read timeout.
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.AuthApiKey`,
            a bearer token, in which case use `weaviate.AuthBearerToken`, a client secret, in which case use `weaviate.AuthClientCredentials`
            or a username and password, in which case use `weaviate.AuthClientPassword`.
        `skip_init_checks`
            Whether to skip the initialisation checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the instance with the required parameters set appropriately.

    Examples:
        >>> import weaviate
        >>> client = weaviate.connect_to_custom(
        ...     http_host="localhost",
        ...     http_port=8080,
        ...     http_secure=False,
        ...     grpc_host="localhost",
        ...     grpc_port=50051,
        ...     grpc_secure=False,
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        ################## With Context Manager #############################
        >>> import weaviate
        >>> with weaviate.connect_to_custom(
        ...     http_host="localhost",
        ...     http_port=8080,
        ...     http_secure=False,
        ...     grpc_host="localhost",
        ...     grpc_port=50051,
        ...     grpc_secure=False,
        ... ) as client:
        ...     client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    client = WeaviateClient(
        ConnectionParams.from_params(
            http_host=http_host,
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=grpc_host,
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
        ),
        auth_client_secret=auth_credentials,
        additional_headers=headers,
        additional_config=additional_config,
        skip_init_checks=skip_init_checks,
    )
    client.connect()
    return client

"""Helper functions for creating new WeaviateClient or WeaviateAsyncClient instances in common scenarios."""
from urllib.parse import urlparse
from typing import Dict, Optional, Tuple

from weaviate.auth import AuthCredentials
from weaviate.client import WeaviateAsyncClient, WeaviateClient
from weaviate.config import AdditionalConfig
from weaviate.connect.base import ConnectionParams, ProtocolParams
from weaviate.embedded import EmbeddedOptions, WEAVIATE_VERSION
from weaviate.validator import _validate_input, _ValidateArgument


def __parse_weaviate_cloud_cluster_url(cluster_url: str) -> Tuple[str, str]:
    _validate_input(_ValidateArgument([str], "cluster_url", cluster_url))
    if cluster_url.startswith("http"):
        # Handle the common case of copy/pasting a URL instead of the hostname.
        cluster_url = urlparse(cluster_url).netloc
    if cluster_url.endswith(".weaviate.network"):
        ident, domain = cluster_url.split(".", 1)
        grpc_host = f"{ident}.grpc.{domain}"
    else:
        grpc_host = f"grpc-{cluster_url}"
    return cluster_url, grpc_host


def connect_to_weaviate_cloud(
    cluster_url: str,
    auth_credentials: Optional[AuthCredentials],
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    skip_init_checks: bool = False,
) -> WeaviateClient:
    """
    Connect to a Weaviate Cloud (WCD) instance.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `cluster_url`
            The WCD cluster URL or hostname to connect to. Usually in the form: rAnD0mD1g1t5.something.weaviate.cloud
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.
        `headers`
            Additional headers to include in the requests, e.g. API keys for third-party Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the cluster with the required parameters set appropriately.

    Examples:
        >>> ################## Without Context Manager #############################
        >>> import weaviate
        >>> client = weaviate.connect_to_weaviate_cloud(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        >>> ################## With Context Manager #############################
        >>> import weaviate
        >>> with weaviate.connect_to_weaviate_cloud(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
        ... ) as client:
        ...     client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    cluster_url, grpc_host = __parse_weaviate_cloud_cluster_url(cluster_url)
    return __connect(
        WeaviateClient(
            connection_params=ConnectionParams(
                http=ProtocolParams(host=cluster_url, port=443, secure=True),
                grpc=ProtocolParams(host=grpc_host, port=443, secure=True),
            ),
            auth_client_secret=auth_credentials,
            additional_headers=headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
        )
    )


def connect_to_wcs(
    cluster_url: str,
    auth_credentials: Optional[AuthCredentials],
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    skip_init_checks: bool = False,
) -> WeaviateClient:
    """
    Connect to a Weaviate Cloud (WCD) instance. This method is deprecated and will be removed in a future release. Use `connect_to_weaviate_cloud` instead.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `cluster_url`
            The WCD cluster URL or hostname to connect to. Usually in the form: rAnD0mD1g1t5.something.weaviate.cloud
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.
        `headers`
            Additional headers to include in the requests, e.g. API keys for third-party Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the cluster with the required parameters set appropriately.

    Examples:
        >>> import weaviate
        >>> client = weaviate.connect_to_wcs(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        ################## With Context Manager #############################
        >>> import weaviate
        >>> with weaviate.connect_to_wcs(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
        ... ) as client:
        ...     client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    return connect_to_weaviate_cloud(
        cluster_url, auth_credentials, headers, additional_config, skip_init_checks
    )


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
    Connect to a local Weaviate instance deployed using Docker compose with standard port configurations.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `host`
            The host to use for the underlying REST and GraphQL API calls.
        `port`
            The port to use for the underlying REST and GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the local instance with default parameters set as:

    Examples:
        >>> ################## Without Context Manager #############################
        >>> import weaviate
        >>> client = weaviate.connect_to_local(
        ...     host="localhost",
        ...     port=8080,
        ...     grpc_port=50051,
        ... )
        >>> client.is_ready()
        True
        >>> client.close() # Close the connection when you are done with it.
        >>> ################## With Context Manager #############################
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
    return __connect(
        WeaviateClient(
            connection_params=ConnectionParams(
                http=ProtocolParams(host=host, port=port, secure=False),
                grpc=ProtocolParams(host=host, port=grpc_port, secure=False),
            ),
            additional_headers=headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
            auth_client_secret=auth_credentials,
        )
    )


def connect_to_embedded(
    hostname: str = "127.0.0.1",
    port: int = 8079,
    grpc_port: int = 50050,
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    version: str = WEAVIATE_VERSION,
    persistence_data_path: Optional[str] = None,
    binary_path: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None,
) -> WeaviateClient:
    """
    Connect to an embedded Weaviate instance.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    See [the docs](https://weaviate.io/developers/weaviate/installation/embedded#embedded-options) for more details.

    Arguments:
        `hostname`
            The hostname to use for the underlying REST & GraphQL API calls.
        `port`
            The port to use for the underlying REST and GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `version`
            Weaviate version to be used for the embedded instance.
        `persistence_data_path`
            Directory where the files making up the database are stored.
            When the XDG_DATA_HOME env variable is set, the default value is: `XDG_DATA_HOME/weaviate/`
            Otherwise it is: `~/.local/share/weaviate`
        `binary_path`
            Directory where to download the binary. If deleted, the client will download the binary again.
            When the XDG_CACHE_HOME env variable is set, the default value is: `XDG_CACHE_HOME/weaviate-embedded/`
            Otherwise it is: `~/.cache/weaviate-embedded`
        `environment_variables`
            Additional environment variables to be passed to the embedded instance for configuration.

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
    options = EmbeddedOptions(
        hostname=hostname,
        port=port,
        grpc_port=grpc_port,
        version=version,
        additional_env_vars=environment_variables,
    )
    if persistence_data_path is not None:
        options.persistence_data_path = persistence_data_path
    if binary_path is not None:
        options.binary_path = binary_path
    client = WeaviateClient(
        embedded_options=options,
        additional_headers=headers,
        additional_config=additional_config,
    )
    return __connect(client)


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

    If this is not sufficient for your customization needs then instantiate a `weaviate.WeaviateClient` instance directly.

    This method handles automatically connecting to Weaviate but not automatically closing the connection. Once you are done with the client
    you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in a `with` statement, which will automatically close the connection when the context is exited. See the examples below for details.

    Arguments:
        `http_host`
            The host to use for the underlying REST and GraphQL API calls.
        `http_port`
            The port to use for the underlying REST and GraphQL API calls.
        `http_secure`
            Whether to use https for the underlying REST and GraphQL API calls.
        `grpc_host`
            The host to use for the underlying gRPC API.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `grpc_secure`
            Whether to use a secure channel for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the instance with the required parameters set appropriately.

    Examples:
        >>> ################## Without Context Manager #############################
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
        >>> ################## With Context Manager #############################
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
    return __connect(
        WeaviateClient(
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
    )


def __connect(client: WeaviateClient) -> WeaviateClient:
    try:
        client.connect()
        return client
    except Exception as e:
        client.close()
        raise e


def use_async_with_weaviate_cloud(
    cluster_url: str,
    auth_credentials: Optional[AuthCredentials],
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    skip_init_checks: bool = False,
) -> WeaviateAsyncClient:
    """
    Create an async client object ready to connect to a Weaviate Cloud (WCD) instance.

    This method handles creating the `WeaviateAsyncClient` instance with relevant options to Weaviate Cloud connections but you must manually call `await client.connect()`.
    Once you are done with the client you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in an `async with` statement, which will automatically open/close the connection when the context is entered/exited. See the examples below for details.

    Arguments:
        `cluster_url`
            The WCD cluster URL or hostname to connect to. Usually in the form: rAnD0mD1g1t5.something.weaviate.cloud
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.
        `headers`
            Additional headers to include in the requests, e.g. API keys for third-party Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateAsyncClient`
            The async client ready to connect to the cluster with the required parameters set appropriately.

    Examples:
        >>> ################## Without Context Manager #############################
        >>> import weaviate
        >>> client = weaviate.use_async_with_weaviate_cloud(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
        ... )
        >>> await client.is_ready()
        False # The connection is not ready yet, you must call `await client.connect()` to connect.
        ... await client.connect()
        >>> await client.is_ready()
        True
        >>> await client.close() # Close the connection when you are done with it.
        >>> ################## With Context Manager #############################
        >>> import weaviate
        >>> async with weaviate.use_async_with_weaviate_cloud(
        ...     cluster_url="rAnD0mD1g1t5.something.weaviate.cloud",
        ...     auth_credentials=weaviate.classes.init.Auth.api_key("my-api-key"),
        ... ) as client:
        ...     await client.is_ready()
        True
    """
    cluster_url, grpc_host = __parse_weaviate_cloud_cluster_url(cluster_url)
    return WeaviateAsyncClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(host=cluster_url, port=443, secure=True),
            grpc=ProtocolParams(host=grpc_host, port=443, secure=True),
        ),
        auth_client_secret=auth_credentials,
        additional_headers=headers,
        additional_config=additional_config,
        skip_init_checks=skip_init_checks,
    )


def use_async_with_local(
    host: str = "localhost",
    port: int = 8080,
    grpc_port: int = 50051,
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    skip_init_checks: bool = False,
    auth_credentials: Optional[AuthCredentials] = None,
) -> WeaviateAsyncClient:
    """
    Create an async client object ready to connect to a local Weaviate instance deployed using Docker compose with standard port configurations.

    This method handles creating the `WeaviateAsyncClient` instance with relevant options to Weaviate Cloud connections but you must manually call `await client.connect()`.
    Once you are done with the client you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in an `async with` statement, which will automatically open/close the connection when the context is entered/exited. See the examples below for details.

    Arguments:
        `host`
            The host to use for the underlying REST and GraphQL API calls.
        `port`
            The port to use for the underlying REST and GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.

    Returns
        `weaviate.WeaviateAsyncClient`
            The async client ready to connect to the cluster with the required parameters set appropriately.

    Examples:
        >>> ################## Without Context Manager #############################
        >>> import weaviate
        >>> client = weaviate.use_async_with_local(
        ...     host="localhost",
        ...     port=8080,
        ...     grpc_port=50051,
        ... )
        >>> await client.is_ready()
        False # The connection is not ready yet, you must call `await client.connect()` to connect.
        ... await client.connect()
        >>> await client.is_ready()
        True
        >>> await client.close() # Close the connection when you are done with it.
        >>> ################## With Context Manager #############################
        >>> import weaviate
        >>> async with weaviate.use_async_with_local(
        ...     host="localhost",
        ...     port=8080,
        ...     grpc_port=50051,
        ... ) as client:
        ...     await client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    return WeaviateAsyncClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(host=host, port=port, secure=False),
            grpc=ProtocolParams(host=host, port=grpc_port, secure=False),
        ),
        additional_headers=headers,
        additional_config=additional_config,
        skip_init_checks=skip_init_checks,
        auth_client_secret=auth_credentials,
    )


def use_async_with_embedded(
    hostname: str = "127.0.0.1",
    port: int = 8079,
    grpc_port: int = 50050,
    headers: Optional[Dict[str, str]] = None,
    additional_config: Optional[AdditionalConfig] = None,
    version: str = WEAVIATE_VERSION,
    persistence_data_path: Optional[str] = None,
    binary_path: Optional[str] = None,
    environment_variables: Optional[Dict[str, str]] = None,
) -> WeaviateAsyncClient:
    """
    Create an async client object ready to connect to an embedded Weaviate instance.

    If this is not sufficient for your customization needs then instantiate a `weaviate.WeaviateAsyncClient` instance directly.

    This method handles creating the `WeaviateAsyncClient` instance with relevant options to Weaviate Cloud connections but you must manually call `await client.connect()`.
    Once you are done with the client you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in an `async with` statement, which will automatically open/close the connection when the context is entered/exited. See the examples below for details.

    See [the docs](https://weaviate.io/developers/weaviate/installation/embedded#embedded-options) for more details.

    Arguments:
        `hostname`
            The hostname to use for the underlying REST & GraphQL API calls.
        `port`
            The port to use for the underlying REST and GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `version`
            Weaviate version to be used for the embedded instance.
        `persistence_data_path`
            Directory where the files making up the database are stored.
            When the XDG_DATA_HOME env variable is set, the default value is: `XDG_DATA_HOME/weaviate/`
            Otherwise it is: `~/.local/share/weaviate`
        `binary_path`
            Directory where to download the binary. If deleted, the client will download the binary again.
            When the XDG_CACHE_HOME env variable is set, the default value is: `XDG_CACHE_HOME/weaviate-embedded/`
            Otherwise it is: `~/.cache/weaviate-embedded`
        `environment_variables`
            Additional environment variables to be passed to the embedded instance for configuration.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the embedded instance with the required parameters set appropriately.

    Examples:
        >>> import weaviate
        >>> client = weaviate.use_async_with_embedded(
        ...     port=8080,
        ...     grpc_port=50051,
        ... )
        >>> await client.is_ready()
        False # The connection is not ready yet, you must call `await client.connect()` to connect.
        ... await client.connect()
        >>> await client.is_ready()
        True
        ################## With Context Manager #############################
        >>> import weaviate
        >>> async with weaviate.use_async_with_embedded(
        ...     port=8080,
        ...     grpc_port=50051,
        ... ) as client:
        ...     await client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    options = EmbeddedOptions(
        hostname=hostname,
        port=port,
        grpc_port=grpc_port,
        version=version,
        additional_env_vars=environment_variables,
    )
    if persistence_data_path is not None:
        options.persistence_data_path = persistence_data_path
    if binary_path is not None:
        options.binary_path = binary_path
    client = WeaviateAsyncClient(
        embedded_options=options,
        additional_headers=headers,
        additional_config=additional_config,
    )
    return client


def use_async_with_custom(
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
) -> WeaviateAsyncClient:
    """
    Create an async client object ready to connect to a Weaviate instance with custom connection parameters.

    If this is not sufficient for your customization needs then instantiate a `weaviate.WeaviateAsyncClient` instance directly.

    This method handles creating the `WeaviateAsyncClient` instance with relevant options to Weaviate Cloud connections but you must manually call `await client.connect()`.
    Once you are done with the client you should call `client.close()` to close the connection and free up resources. Alternatively, you can use the client as a context manager
    in an `async with` statement, which will automatically open/close the connection when the context is entered/exited. See the examples below for details.

    Arguments:
        `http_host`
            The host to use for the underlying REST and GraphQL API calls.
        `http_port`
            The port to use for the underlying REST and GraphQL API calls.
        `http_secure`
            Whether to use https for the underlying REST and GraphQL API calls.
        `grpc_host`
            The host to use for the underlying gRPC API.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `grpc_secure`
            Whether to use a secure channel for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorization.
        `additional_config`
            This includes many additional, rarely used config options. use wvc.init.AdditionalConfig() to configure.
        `auth_credentials`
            The credentials to use for authentication with your Weaviate instance. This can be an API key, in which case use `weaviate.classes.init.Auth.api_key()`,
            a bearer token, in which case use `weaviate.classes.init.Auth.bearer_token()`, a client secret, in which case use `weaviate.classes.init.Auth.client_credentials()`
            or a username and password, in which case use `weaviate.classes.init.Auth.client_password()`.
        `skip_init_checks`
            Whether to skip the initialization checks when connecting to Weaviate.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the instance with the required parameters set appropriately.

    Examples:
        >>> ################## Without Context Manager #############################
        >>> import weaviate
        >>> client = weaviate.use_async_with_custom(
        ...     http_host="localhost",
        ...     http_port=8080,
        ...     http_secure=False,
        ...     grpc_host="localhost",
        ...     grpc_port=50051,
        ...     grpc_secure=False,
        ... )
        >>> await client.is_ready()
        False # The connection is not ready yet, you must call `await client.connect()` to connect.
        ... await client.connect()
        >>> await client.is_ready()
        True
        >>> await client.close() # Close the connection when you are done with it.
        >>> ################## Async With Context Manager #############################
        >>> import weaviate
        >>> async with weaviate.use_async_with_custom(
        ...     http_host="localhost",
        ...     http_port=8080,
        ...     http_secure=False,
        ...     grpc_host="localhost",
        ...     grpc_port=50051,
        ...     grpc_secure=False,
        ... ) as client:
        ...     await client.is_ready()
        True
        >>> # The connection is automatically closed when the context is exited.
    """
    return WeaviateAsyncClient(
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

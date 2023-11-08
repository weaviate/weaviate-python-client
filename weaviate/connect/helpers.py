from typing import Optional, Tuple

from weaviate.auth import AuthCredentials
from weaviate.client import WeaviateClient
from weaviate.config import AdditionalConfig
from weaviate.connect.connection import ConnectionParams, ProtocolParams
from weaviate.embedded import EmbeddedOptions


def connect_to_wcs(
    cluster_id: str,
    auth_credentials: Optional[AuthCredentials],
    headers: Optional[dict] = None,
    timeout: Tuple[int, int] = (10, 60),
) -> WeaviateClient:
    """
    Connect to your own Weaviate Cloud Service (WCS) instance.

    Arguments:
        `cluster_id`
            The WCS cluster id to connect to.
        `auth_credentials`
            The credentials to use for authentication with your WCS instance. This can be an API key, in which case use `weaviate.auth.AuthApiKey`,
            a bearer token, in which case use `weaviate.auth.AuthBearerToken`, a client secret, in which case use `weaviate.auth.AuthClientCredentials`
            or a username and password, in which case use `weaviate.auth.AuthClientPassword`.
        `headers`
            Additional headers to include in the requests, e.g. API keys for third-party Cloud vectorisation.
        `timeout`
            The timeout to use for the underlying HTTP calls. Accepts a tuple of integers, where the first integer
            represents the connect timeout and the second integer represents the read timeout.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the cluster with the required parameters set appropriately.
    """
    raise NotImplementedError("WCS doesn't support gRPC yet")
    # return WeaviateClient(
    #     connection_params=ConnectionParams(
    #         http=ProtocolParams(host=f"{cluster_id}.weaviate.network", port=443, secure=True),
    #         grpc=ProtocolParams(host=f"{cluster_id}.weaviate.network", port=50051, secure=True),
    #     ),
    #     auth_client_secret=auth_credentials,
    #     additional_headers=headers,
    #     additional_config=AdditionalConfig(timeout=timeout),
    # )


def connect_to_local(
    host: str = "localhost",
    port: int = 8080,
    grpc_port: int = 50051,
    headers: Optional[dict] = None,
    timeout: Tuple[int, int] = (10, 60),
) -> WeaviateClient:
    """
    Connect to a local Weaviate instance deployed using Docker compose with standard port configurations.

    Arguments:
        `schema`
            The schema to use for the underlying REST & GraphQL API calls.
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

    Returns
        `weaviate.WeaviateClient`
            The client connected to the local instance with default parameters set as:
    """
    return WeaviateClient(
        connection_params=ConnectionParams(
            http=ProtocolParams(host=host, port=port, secure=False),
            grpc=ProtocolParams(host=host, port=grpc_port, secure=False),
        ),
        additional_headers=headers,
        additional_config=AdditionalConfig(timeout=timeout),
    )


def connect_to_embedded(
    port: int = 8079,
    grpc_port: int = 50051,
    headers: Optional[dict] = None,
    timeout: Tuple[int, int] = (10, 60),
    version: str = "1.22.3",
) -> WeaviateClient:
    """
    Connect to an embedded Weaviate instance.

    Arguments:
        `port`
            The port to use for the underlying REST & GraphQL API calls.
        `grpc_port`
            The port to use for the underlying gRPC API.
        `headers`
            Additional headers to include in the requests, e.g. API keys for Cloud vectorisation.
        `timeout`
            The timeout to use for the underlying HTTP calls. Accepts a tuple of integers, where the first integer
            represents the connect timeout and the second integer represents the read timeout.

    Returns
        `weaviate.WeaviateClient`
            The client connected to the embedded instance with the required parameters set appropriately.
    """
    return WeaviateClient(
        embedded_options=EmbeddedOptions(
            port=port,
            grpc_port=grpc_port,
            version=version,
        ),
        additional_headers=headers,
        additional_config=AdditionalConfig(timeout=timeout),
    )


def connect_to_custom(
    http_host: str,
    http_port: int,
    http_secure: bool,
    grpc_host: str,
    grpc_port: int,
    grpc_secure: bool,
    headers: Optional[dict] = None,
    timeout: Tuple[int, int] = (10, 60),
) -> WeaviateClient:
    """
    Connect to a Weaviate instance with custom connection parameters.

    If this is not sufficient for your customisation needs then instantiate a `weaviate.WeaviateClient` directly.

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

    Returns
        `weaviate.WeaviateClient`
            The client connected to the instance with the required parameters set appropriately.
    """
    return WeaviateClient(
        ConnectionParams.from_params(
            http_host=http_host,
            http_port=http_port,
            http_secure=http_secure,
            grpc_host=grpc_host,
            grpc_port=grpc_port,
            grpc_secure=grpc_secure,
        ),
        additional_headers=headers,
        additional_config=AdditionalConfig(timeout=timeout),
    )

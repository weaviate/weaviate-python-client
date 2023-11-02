"""
Weaviate Python Client Library used to interact with a Weaviate instance.
"""


__all__ = [
    "Client",
    "Collection",
    "Connect",
    "WeaviateClient",
    "AuthClientCredentials",
    "AuthClientPassword",
    "AuthBearerToken",
    "AuthApiKey",
    "UnexpectedStatusCodeException",
    "ObjectAlreadyExistsException",
    "AuthenticationFailedException",
    "SchemaValidationException",
    "WeaviateStartUpError",
    "ConsistencyLevel",
    "WeaviateErrorRetryConf",
    "EmbeddedOptions",
    "AdditionalConfig",
    "Config",
    "ConnectionConfig",
    "ConnectionParams",
    "ProtocolParams",
    "AdditionalProperties",
    "LinkTo",
    "Tenant",
    "TenantActivityStatus",
    "connect_to_custom",
    "connect_to_embedded",
    "connect_to_local",
    "connect_to_wcs",
]

import sys

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("weaviate-client")
except PackageNotFoundError:
    __version__ = "unknown version"

from .auth import AuthClientCredentials, AuthClientPassword, AuthBearerToken, AuthApiKey
from .batch.crud_batch import WeaviateErrorRetryConf
from .client import Client, WeaviateClient
from .collections.collection import Collection
from .connect.connection import ConnectionParams, ProtocolParams
from .data.replication import ConsistencyLevel
from .schema.crud_schema import Tenant, TenantActivityStatus
from .connect.helpers import (
    connect_to_custom,
    connect_to_embedded,
    connect_to_local,
    connect_to_wcs,
)
from .embedded import EmbeddedOptions
from .exceptions import (
    UnexpectedStatusCodeException,
    ObjectAlreadyExistsException,
    AuthenticationFailedException,
    SchemaValidationException,
    WeaviateStartUpError,
)
from .config import AdditionalConfig, Config, ConnectionConfig
from .gql.get import AdditionalProperties, LinkTo

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("default")

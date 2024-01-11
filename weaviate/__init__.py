"""
Weaviate Python Client Library used to interact with a Weaviate instance.
"""


__all__ = [
    "Client",
    "Collection",
    "WeaviateClient",
    "AuthClientCredentials",
    "AuthClientPassword",
    "AuthBearerToken",
    "AuthApiKey",
    "BackupStorage",
    "UnexpectedStatusCodeError",
    "ObjectAlreadyExists",
    "AuthenticationFailed",
    "SchemaValidationError",
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
    "Shard",
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
from .client import Client, WeaviateClient
from .collections.collection import Collection
from .connect.connection import ConnectionParams, ProtocolParams
from .batch.crud_batch import WeaviateErrorRetryConf, Shard
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
    UnexpectedStatusCodeError,
    ObjectAlreadyExists,
    AuthenticationFailed,
    SchemaValidationError,
    WeaviateStartUpError,
)
from .config import AdditionalConfig, Config, ConnectionConfig
from .gql.get import AdditionalProperties, LinkTo
from .backup.backup import BackupStorage

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("default")

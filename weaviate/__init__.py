"""
Weaviate Python Client Library used to interact with a Weaviate instance.
"""

import sys
from importlib.metadata import version, PackageNotFoundError
from typing import Any

try:
    __version__ = version("weaviate-client")
except PackageNotFoundError:
    __version__ = "unknown version"

from .client import Client, WeaviateClient
from .connect.helpers import (
    connect_to_custom,
    connect_to_embedded,
    connect_to_local,
    connect_to_wcs,
)

from . import backup, batch, classes, cluster, collections, connect, data, gql, outputs, schema

import warnings

if not sys.warnoptions:
    warnings.simplefilter("default")

from .warnings import _Warnings

__all__ = [
    "Client",
    "WeaviateClient",
    "connect_to_custom",
    "connect_to_embedded",
    "connect_to_local",
    "connect_to_wcs",
    "backup",
    "batch",
    "classes",
    "cluster",
    "collections",
    "connect",
    "data",
    "gql",
    "outputs",
    "schema",
]

deprs = [
    "Collection",
    "AuthClientCredentials",
    "AuthClientPassword",
    "AuthBearerToken",
    "AuthApiKey",
    "BackupStorage",
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
    "Shard",
    "Tenant",
    "TenantActivityStatus",
]

map_ = {
    "Collection": "collections.collection",
    "AuthClientCredentials": "auth",
    "AuthClientPassword": "auth",
    "AuthBearerToken": "auth",
    "AuthApiKey": "auth",
    "BackupStorage": "backup.backup",
    "UnexpectedStatusCodeException": "exceptions",
    "ObjectAlreadyExistsException": "exceptions",
    "AuthenticationFailedException": "exceptions",
    "SchemaValidationException": "exceptions",
    "WeaviateStartUpError": "exceptions",
    "ConsistencyLevel": "data.replication",
    "WeaviateErrorRetryConf": "batch.crud_batch",
    "EmbeddedOptions": "embedded",
    "AdditionalConfig": "config",
    "Config": "config",
    "ConnectionConfig": "config",
    "ConnectionParams": "connect.base",
    "ProtocolParams": "connect.base",
    "AdditionalProperties": "gql.get",
    "LinkTo": "gql.get",
    "Shard": "batch.crud_batch",
    "Tenant": "schema.crud_schema",
    "TenantActivityStatus": "schema.crud_schema",
}


def __getattr__(name: str) -> Any:
    if name in deprs:
        _Warnings.root_module_import(name, map_[name].split(".")[0])
        return getattr(sys.modules[f"{__name__}.{map_[name]}"], name)
    raise AttributeError(f"module {__name__} has no attribute {name}")

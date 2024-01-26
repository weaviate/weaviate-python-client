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

from . import (
    auth,
    backup,
    batch,
    classes,
    cluster,
    collections,
    config,
    connect,
    data,
    embedded,
    exceptions,
    gql,
    outputs,
    schema,
    types,
)

if not sys.warnoptions:
    from warnings import simplefilter

    simplefilter("default")

from .warnings import _Warnings

__all__ = [
    "Client",
    "WeaviateClient",
    "connect_to_custom",
    "connect_to_embedded",
    "connect_to_local",
    "connect_to_wcs",
    "auth",
    "backup",
    "batch",
    "classes",
    "cluster",
    "collections",
    "config",
    "connect",
    "data",
    "embedded",
    "exceptions",
    "gql",
    "outputs",
    "schema",
    "types",
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
    "Collection": "collections",
    "AuthClientCredentials": "auth",
    "AuthClientPassword": "auth",
    "AuthBearerToken": "auth",
    "AuthApiKey": "auth",
    "BackupStorage": "backup",
    "UnexpectedStatusCodeException": "exceptions",
    "ObjectAlreadyExistsException": "exceptions",
    "AuthenticationFailedException": "exceptions",
    "SchemaValidationException": "exceptions",
    "WeaviateStartUpError": "exceptions",
    "ConsistencyLevel": "data",
    "WeaviateErrorRetryConf": "batch",
    "EmbeddedOptions": "embedded",
    "AdditionalConfig": "config",
    "Config": "config",
    "ConnectionConfig": "config",
    "ConnectionParams": "connect",
    "ProtocolParams": "connect",
    "AdditionalProperties": "gql",
    "LinkTo": "gql",
    "Shard": "batch",
    "Tenant": "schema",
    "TenantActivityStatus": "schema",
}


def __getattr__(name: str) -> Any:
    if name in deprs:
        _Warnings.root_module_import(name, map_[name])
        return getattr(sys.modules[f"{__name__}.{map_[name]}"], name)
    raise AttributeError(f"module {__name__} has no attribute {name}")

"""Weaviate Python Client Library used to interact with a Weaviate instance."""

import sys

# Must run before every other import: under Pyodide there is no grpcio wheel, and importing
# the companion installs the pure-Python grpc shim that everything below resolves against.
if sys.platform == "emscripten":
    try:
        import weaviate_client_web  # noqa: F401
    except ImportError as exc:
        from importlib.util import find_spec

        # Only an absent companion earns the install hint; a companion that is present
        # but fails to import (a broken dependency of its own) must surface that error.
        if not (isinstance(exc, ModuleNotFoundError) and exc.name == "weaviate_client_web"):
            raise
        if find_spec("grpc") is None:
            raise ImportError(
                "weaviate requires the weaviate-client-web package under "
                "WebAssembly/Pyodide: there is no grpcio wheel for Emscripten, and "
                "weaviate-client-web provides the grpc-web (fetch) transport in its "
                "place. Install it (e.g. micropip.install('weaviate-client-web')) and "
                "import weaviate again."
            ) from exc

import os
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from . import _authlib_compat  # noqa: F401  # side-effect: silence authlib.jose deprecation

try:
    __version__ = version("weaviate-client")
except PackageNotFoundError:
    __version__ = "unknown version"

from . import (
    auth,
    backup,
    classes,
    cluster,
    collections,
    config,
    connect,
    embedded,
    exceptions,
    outputs,
    tokenization,
    types,
)
from .client import Client, WeaviateAsyncClient, WeaviateClient
from .collections.batch.client import BatchClient, ClientBatchingContextManager
from .connect.helpers import (
    connect_to_custom,
    connect_to_embedded,
    connect_to_local,
    connect_to_wcs,
    connect_to_weaviate_cloud,
    use_async_with_custom,
    use_async_with_embedded,
    use_async_with_local,
    use_async_with_weaviate_cloud,
)

if not sys.warnoptions:
    from warnings import simplefilter

    simplefilter("default")

from .warnings import _Warnings

os.environ["GRPC_VERBOSITY"] = "ERROR"  # https://github.com/danielmiessler/fabric/discussions/754

__all__ = [
    "BatchClient",
    "ClientBatchingContextManager",
    "Client",
    "WeaviateClient",
    "WeaviateAsyncClient",
    "connect_to_custom",
    "connect_to_embedded",
    "connect_to_local",
    "connect_to_wcs",
    "connect_to_weaviate_cloud",
    "auth",
    "backup",
    "classes",
    "cluster",
    "collections",
    "config",
    "connect",
    "embedded",
    "exceptions",
    "outputs",
    "tokenization",
    "types",
    "use_async_with_custom",
    "use_async_with_embedded",
    "use_async_with_local",
    "use_async_with_weaviate_cloud",
]

try:
    import weaviate_agents as agents

    sys.modules["weaviate.agents"] = agents
    __all__.append("agents")
except ImportError:
    pass


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

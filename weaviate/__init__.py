"""
Weaviate Python Client Library used to interact with a Weaviate instance.

The interaction with Weaviate instance should be through a `Client` object. A `Client` instance
has instance attributes to all the object needed to create objects/schema, do classification,
upload batches, query data, ... Creating separate `Schema`, `DataObject`, `Batch`,
`Classification`, `Query`, `Connect`, `Reference` is **STRONGLY DISCOURAGED**. The `Client` class
creates the needed instances and connects all of them to the same Weaviate instance for you.

Examples
--------
Creating and exploring a Weaviate instance running on `localhost`, on port `8080`, with Authentication disabled.

>>> import weaviate
>>> client = weaviate.Client('http://localhost:8080')
>>> print_type = lambda obj: print(type(obj))
>>> print_type(client.batch)
<class 'weaviate.batch.crud_batch.Batch'>
>>> print_type(client.schema)
<class 'weaviate.schema.crud_schema.Schema'>
>>> print_type(client.classification)
<class 'weaviate.classification.classify.Classification'>
>>> print_type(client.data_object)
<class 'weaviate.data.crud_data.DataObject'>
>>> print_type(client.query)
<class 'weaviate.gql.query.Query'>

Attributes
----------
__version__ : str
    Current `weaviate-python` library version installed.
"""


__all__ = [
    "Client",
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
from .connect.connection import ConnectionParams, ProtocolParams
from .connect.helpers import (
    connect_to_custom,
    connect_to_embedded,
    connect_to_local,
    connect_to_wcs,
)
from .data.replication import ConsistencyLevel
from .schema.crud_schema import Tenant, TenantActivityStatus
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

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
    "Config",
    "ConnectionConfig",
    "AdditionalProperties",
    "LinkTo",
    "Shard",
    "Tenant",
    "TenantActivityStatus",
]

import sys

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("weaviate-client")
except PackageNotFoundError:
    __version__ = "unknown version"

from .auth import AuthClientCredentials, AuthClientPassword, AuthBearerToken, AuthApiKey
from .batch.crud_batch import WeaviateErrorRetryConf, Shard
from .client import Client
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
from .config import Config, ConnectionConfig
from .gql.get import AdditionalProperties, LinkTo

if not sys.warnoptions:
    import warnings

    warnings.simplefilter("default")

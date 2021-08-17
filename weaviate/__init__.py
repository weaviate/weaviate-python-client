"""
Weaviate Python Client Library used to interact with a Weaviate instance.

The interaction with Weaviate instance should be through a `Client` object. A `Client` instance
has instance attributes to all the object needed to create objects/schema, do classification,
upload batches, query data, ... Creating separate `Schema`, `DataObject`, `Batch`,
`Classification`, `Query`, `Connect`, `Reference` is **STRONGLY DISCOURAGED**. The `Client` class
creates the needed instances and connects all of them to the same Weaviate instance for you.

Examples
--------
A Weaviate instance running on `localhost`, on port `8080`. With Authentication disables.

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
    'Client',
    'AuthClientCredentials',
    'AuthClientPassword',
    'UnexpectedStatusCodeException',
    'ObjectAlreadyExistsException',
    'AuthenticationFailedException',
    'SchemaValidationException',
]

from .version import __version__
from .exceptions import *
from .auth import AuthClientCredentials, AuthClientPassword
from .client import Client

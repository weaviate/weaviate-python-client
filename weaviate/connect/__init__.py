#__all__ = ["connection"]

REST_METHOD_GET = 0
REST_METHOD_PUT = 1
REST_METHOD_POST = 2

from weaviate.connect.util import get_epoch_time
from weaviate.connect.connection import Connection
from weaviate import errors

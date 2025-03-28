from typing import (
    Generic,
)

from weaviate.collections.data.executor import _DataExecutor
from weaviate.connect.v4 import ConnectionType


class _DataBase(Generic[ConnectionType], _DataExecutor):
    pass

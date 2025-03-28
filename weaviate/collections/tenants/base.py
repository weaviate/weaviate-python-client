from typing import Generic

from weaviate.collections.tenants.executor import (
    _TenantsExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _TenantsBase(Generic[ConnectionType], _TenantsExecutor):
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        validate_arguments: bool,
    ) -> None:
        super().__init__(connection, name, validate_arguments)

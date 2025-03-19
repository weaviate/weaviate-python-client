from math import ceil
from typing import Any, Dict, Generic, List, Optional, Sequence, Union

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.tenants import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantActivityStatus,
    TenantCreateActivityStatus,
    TenantUpdateActivityStatus,
    TenantOutput,
)
from weaviate.collections.grpc.tenants import _TenantsGRPC
from weaviate.collections.tenants.executor import _TenantsExecutor
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, ConnectionType
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import tenants_pb2
from weaviate.validator import _validate_input, _ValidateArgument

TenantCreateInputType = Union[str, Tenant, TenantCreate]
TenantUpdateInputType = Union[Tenant, TenantUpdate]
TenantOutputType = Tenant

UPDATE_TENANT_BATCH_SIZE = 100


class _TenantsBase(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        validate_arguments: bool,
    ) -> None:
        self._connection = connection
        self.name = name
        self._executor = _TenantsExecutor(
            weaviate_version=connection._weaviate_version,
            name=name,
            consistency_level=consistency_level,
            validate_arguments=validate_arguments,
        )


class _TenantsAsync(_TenantsBase[ConnectionAsync]):
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    async def create(
        self, tenants: Union[TenantCreateInputType, Sequence[TenantCreateInputType]]
    ) -> None:
        """Create the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                A tenant name, `wvc.config.tenants.Tenant`, `wvc.config.tenants.TenantCreateInput` object, or a list of tenants names
                and/or `wvc.config.tenants.Tenant` objects to add to the given collection.
                If a string is provided, the tenant will be added with the default activity status of `HOT`.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of `wvc.Tenant` objects.
        """
        return await self._executor.create(connection=self._connection, tenants=tenants)

    async def remove(self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]) -> None:
        """Remove the specified tenants from a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                A tenant name, `wvc.config.tenants.Tenant` object, or a list of tenants names
                and/or `wvc.config.tenants.Tenant` objects to remove from the given class.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of strings.
        """
        return await self._executor.remove(connection=self._connection, tenants=tenants)

    async def get(self) -> Dict[str, TenantOutputType]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return await self._executor.get(connection=self._connection)

    async def get_by_names(
        self, tenants: Sequence[Union[str, Tenant]]
    ) -> Dict[str, TenantOutputType]:
        """Return named tenants currently associated with a collection in Weaviate.

        If the tenant does not exist, it will not be included in the response.
        If no names are provided, all tenants will be returned.
        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                Sequence of tenant names of wvc.tenants.Tenant objects to retrieve. To retrieve all tenants, use the `get` method.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return await self._executor.get_by_names(connection=self._connection, tenants=tenants)

    async def get_by_name(self, tenant: Union[str, Tenant]) -> Optional[TenantOutputType]:
        """Return a specific tenant associated with a collection in Weaviate.

        If the tenant does not exist, `None` will be returned.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenant`
                The tenant to retrieve.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return await self._executor.get_by_name(connection=self._connection, tenant=tenant)

    async def update(
        self, tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]]
    ) -> None:
        """Update the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                A tenant name, `wvc.config.tenants.Tenant` object, or a list of tenants names
                and/or `wvc.config.tenants.Tenant` objects to update for the given collection.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of `wvc.Tenant` objects.
        """
        return await self._executor.update(connection=self._connection, tenants=tenants)

    async def exists(self, tenant: Union[str, Tenant]) -> bool:
        """Check if a tenant exists for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenant`
                Tenant name or `wvc.config.tenants.Tenant` object to check for existence.

        Returns:
            `bool`
                `True` if the tenant exists, `False` otherwise.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return await self._executor.exists(connection=self._connection, tenant=tenant)

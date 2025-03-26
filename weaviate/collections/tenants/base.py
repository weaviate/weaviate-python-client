from abc import abstractmethod
from typing import Dict, Generic, Optional, Sequence, Union

from weaviate.collections.classes.tenants import (
    Tenant,
)
from weaviate.collections.tenants.executor import (
    _TenantsExecutor,
    TenantCreateInputType,
    TenantOutputType,
    TenantUpdateInputType,
)
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType


class _TenantsBase(Generic[ConnectionType]):
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
        self._connection = connection
        self.name = name
        self._executor = _TenantsExecutor(
            weaviate_version=connection._weaviate_version,
            name=name,
            validate_arguments=validate_arguments,
        )

    @abstractmethod
    def create(
        self, tenants: Union[TenantCreateInputType, Sequence[TenantCreateInputType]]
    ) -> ExecutorResult[None]:
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
        raise NotImplementedError()

    @abstractmethod
    def remove(
        self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]
    ) -> ExecutorResult[None]:
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
        raise NotImplementedError()

    @abstractmethod
    def get(self) -> ExecutorResult[Dict[str, TenantOutputType]]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_by_names(
        self, tenants: Sequence[Union[str, Tenant]]
    ) -> ExecutorResult[Dict[str, TenantOutputType]]:
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
        raise NotImplementedError()

    @abstractmethod
    def get_by_name(self, tenant: Union[str, Tenant]) -> ExecutorResult[Optional[TenantOutputType]]:
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
        raise NotImplementedError()

    @abstractmethod
    def update(
        self, tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]]
    ) -> ExecutorResult[None]:
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
        raise NotImplementedError()

    @abstractmethod
    def exists(self, tenant: Union[str, Tenant]) -> ExecutorResult[bool]:
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
        raise NotImplementedError()

from typing import Dict, List, Optional, Sequence, Union

from weaviate.collections.classes.tenants import Tenant

from weaviate.event_loop import _EventLoop
from weaviate.collections.tenants.asy import _TenantsAsync


class _Tenants:
    def __init__(self, loop: _EventLoop, tenants: "_TenantsAsync"):
        self._loop = loop
        self._tenants = tenants

    def create(self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]) -> None:
        """Create the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenants to add to the given collection.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of `wvc.Tenant` objects.
        """
        self._loop.run_until_complete(self._tenants.create, tenants)

    def remove(self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]) -> None:
        """Remove the specified tenants from a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenant names to remove from the given class.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of strings.
        """
        self._loop.run_until_complete(self._tenants.remove, tenants)

    def get(self) -> Dict[str, Tenant]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        return self._loop.run_until_complete(self._tenants.get)

    def update(self, tenants: Union[Tenant, List[Tenant]]) -> None:
        """Update the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                List of tenants to update for the given collection.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
            `weaviate.WeaviateInvalidInputError`
                If `tenants` is not a list of `wvc.Tenant` objects.
        """
        self._loop.run_until_complete(self._tenants.update, tenants)

    def get_by_names(self, tenants: Sequence[Union[str, Tenant]]) -> Dict[str, Tenant]:
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
        return self._loop.run_until_complete(self._tenants.get_by_names, tenants)

    def get_by_name(self, tenant: Union[str, Tenant]) -> Optional[Tenant]:
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
        return self._loop.run_until_complete(self._tenants.get_by_name, tenant)

    def exists(self, tenant: Union[str, Tenant]) -> bool:
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
        return self._loop.run_until_complete(self._tenants.exists, tenant)

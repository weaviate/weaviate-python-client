from typing import Dict, Any, List, Union

from weaviate.collections.classes.tenants import Tenant, TenantActivityStatus
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.exceptions import WeaviateNotImplementedError


class _Tenants:
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    def __init__(self, connection: ConnectionV4, name: str) -> None:
        self.__connection = connection
        self.__name = name

    def create(self, tenants: Union[str, Tenant, List[Union[str, Tenant]]]) -> None:
        """Create the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenants`
                A tenant name, `wvc.config.tenants.Tenant` object, or a list of tenants names
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
        _validate_input(
            [
                _ValidateArgument(
                    expected=[str, Tenant, List[Union[str, Tenant]]], name="tenants", value=tenants
                )
            ]
        )

        loaded_tenants = (
            [
                tenant.model_dump()
                if isinstance(tenant, Tenant)
                else {"name": tenant, "activityStatus": TenantActivityStatus.HOT}
                for tenant in tenants
            ]
            if isinstance(tenants, list)
            else [
                {"name": tenants, "activityStatus": TenantActivityStatus.HOT}
                if isinstance(tenants, str)
                else tenants.model_dump()
            ]
        )

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.post(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been added properly for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Add collection tenants for {self.__name}"
            ),
        )

    def remove(self, tenants: Union[str, Tenant, List[Union[str, Tenant]]]) -> None:
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
        _validate_input(
            [
                _ValidateArgument(
                    expected=[str, Tenant, List[Union[str, Tenant]]], name="tenants", value=tenants
                )
            ]
        )

        loaded_tenants = (
            [tenant.name if isinstance(tenant, Tenant) else tenant for tenant in tenants]
            if isinstance(tenants, list)
            else [tenants if isinstance(tenants, str) else tenants.name]
        )

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.delete(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been deleted for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self.__name}"
            ),
        )

    def get(self) -> Dict[str, Tenant]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        path = "/schema/" + self.__name + "/tenants"
        response = self.__connection.get(
            path=path,
            error_msg=f"Could not get collection tenants for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Get collection tenants for {self.__name}"
            ),
        )

        tenant_resp: List[Dict[str, Any]] = response.json()
        return {tenant["name"]: Tenant(**tenant) for tenant in tenant_resp}

    def update(self, tenants: Union[Tenant, List[Tenant]]) -> None:
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
        _validate_input(
            [_ValidateArgument(expected=[Tenant, List[Tenant]], name="tenants", value=tenants)]
        )

        loaded_tenants = (
            [tenant.model_dump() for tenant in tenants]
            if isinstance(tenants, list)
            else [tenants.model_dump()]
        )

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.put(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been updated properly for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Update collection tenants for {self.__name}"
            ),
        )

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
        if self.__connection._weaviate_version.is_lower_than(
            1, 24, 5
        ):  # change to 1.25.0 when it lands
            raise WeaviateNotImplementedError(
                "tenants.exists", str(self.__connection._weaviate_version), "1.25.0"
            )

        tenant_name = tenant.name if isinstance(tenant, Tenant) else tenant

        path = "/schema/" + self.__name + "/tenants/" + tenant_name
        response = self.__connection.head(
            path=path,
            error_msg=f"Could not check if tenant exists for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404], error=f"Check if tenant exists for {self.__name}"
            ),  # allow 404 to perform bool check on response code
        )
        return response.status_code == 200

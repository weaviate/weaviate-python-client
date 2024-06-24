from typing import Any, Dict, List, Optional, Sequence, Union

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.grpc.tenants import _TenantsGRPC

from weaviate.collections.classes.tenants import Tenant, TenantActivityStatus
from weaviate.validator import _validate_input, _ValidateArgument

from weaviate.connect.v4 import _ExpectedStatusCodes

from weaviate.connect import ConnectionV4


class _TenantsBase:
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        validate_arguments: bool = True,
    ) -> None:
        self._connection = connection
        self._name = name
        self._grpc = _TenantsGRPC(
            connection=connection,
            name=name,
            consistency_level=consistency_level,
        )
        self._validate_arguments = validate_arguments


class _TenantsAsync(_TenantsBase):
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    async def create(self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]) -> None:
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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        expected=[str, Tenant, Sequence[Union[str, Tenant]]],
                        name="tenants",
                        value=tenants,
                    )
                ]
            )

        loaded_tenants: List[dict] = []
        if isinstance(tenants, str):
            loaded_tenants = [{"name": tenants, "activityStatus": TenantActivityStatus.HOT}]
        elif isinstance(tenants, Tenant):
            loaded_tenants = [tenants.model_dump()]
        else:
            loaded_tenants = [
                tenant.model_dump()
                if isinstance(tenant, Tenant)
                else {"name": tenant, "activityStatus": TenantActivityStatus.HOT}
                for tenant in tenants
            ]

        path = "/schema/" + self._name + "/tenants"
        await self._connection.post(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been added properly for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Add collection tenants for {self._name}"
            ),
        )

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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        expected=[str, Tenant, Sequence[Union[str, Tenant]]],
                        name="tenants",
                        value=tenants,
                    )
                ]
            )

        loaded_tenants: List[str] = []
        if isinstance(tenants, str):
            loaded_tenants = [tenants]
        elif isinstance(tenants, Tenant):
            loaded_tenants = [tenants.name]
        else:
            loaded_tenants = [
                tenant.name if isinstance(tenant, Tenant) else tenant for tenant in tenants
            ]

        path = "/schema/" + self._name + "/tenants"
        await self._connection.delete(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been deleted for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self._name}"
            ),
        )

    async def __get_with_rest(self) -> Dict[str, Tenant]:
        path = "/schema/" + self._name + "/tenants"
        response = await self._connection.get(
            path=path,
            error_msg=f"Could not get collection tenants for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Get collection tenants for {self._name}"
            ),
        )

        tenant_resp: List[Dict[str, Any]] = response.json()
        return {tenant["name"]: Tenant(**tenant) for tenant in tenant_resp}

    async def __get_with_grpc(
        self, tenants: Optional[Sequence[Union[str, Tenant]]] = None
    ) -> Dict[str, Tenant]:
        response = await self._grpc.get(
            names=[tenant.name if isinstance(tenant, Tenant) else tenant for tenant in tenants]
            if tenants is not None
            else tenants
        )

        return {
            tenant.name: Tenant(
                name=tenant.name,
                activity_status=self._grpc.map_activity_status(tenant.activity_status),
            )
            for tenant in response.tenants
        }

    async def get(self) -> Dict[str, Tenant]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        if self._connection._weaviate_version.supports_tenants_get_grpc:
            return await self.__get_with_grpc()
        else:
            return await self.__get_with_rest()

    async def get_by_names(self, tenants: Sequence[Union[str, Tenant]]) -> Dict[str, Tenant]:
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
        self._connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_names' method")
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Sequence[Union[str, Tenant]]], name="names", value=tenants
                )
            )
        return await self.__get_with_grpc(tenants=tenants)

    async def get_by_name(self, tenant: Union[str, Tenant]) -> Optional[Tenant]:
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
        self._connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_name' method")
        response = await self._grpc.get(
            names=[tenant.name if isinstance(tenant, Tenant) else tenant]
        )
        if len(response.tenants) == 0:
            return None
        return Tenant(
            name=response.tenants[0].name,
            activity_status=self._grpc.map_activity_status(response.tenants[0].activity_status),
        )

    async def update(self, tenants: Union[Tenant, List[Tenant]]) -> None:
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
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(expected=[Tenant, List[Tenant]], name="tenants", value=tenants)
            )

        loaded_tenants = (
            [tenants.model_dump()]
            if isinstance(tenants, Tenant)
            else [tenant.model_dump() for tenant in tenants]
        )

        path = "/schema/" + self._name + "/tenants"
        await self._connection.put(
            path=path,
            weaviate_object=loaded_tenants,
            error_msg=f"Collection tenants may not have been updated properly for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Update collection tenants for {self._name}"
            ),
        )

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
        self._connection._weaviate_version.check_is_at_least_1_25_0("The 'exists' method")

        tenant_name = tenant.name if isinstance(tenant, Tenant) else tenant

        path = "/schema/" + self._name + "/tenants/" + tenant_name
        response = await self._connection.head(
            path=path,
            error_msg=f"Could not check if tenant exists for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404], error=f"Check if tenant exists for {self._name}"
            ),  # allow 404 to perform bool check on response code
        )
        return response.status_code == 200

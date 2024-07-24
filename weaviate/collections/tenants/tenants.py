from math import ceil
from typing import Any, Dict, List, Optional, Sequence, Union

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
from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.validator import _validate_input, _ValidateArgument

TenantCreateInputType = Union[str, Tenant, TenantCreate]
TenantUpdateInputType = Union[Tenant, TenantUpdate]
TenantOutputType = Tenant

UPDATE_TENANT_BATCH_SIZE = 100


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
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        expected=[
                            str,
                            Tenant,
                            TenantCreate,
                            Sequence[Union[str, Tenant, TenantCreate]],
                        ],
                        name="tenants",
                        value=tenants,
                    )
                ]
            )

        path = "/schema/" + self._name + "/tenants"
        await self._connection.post(
            path=path,
            weaviate_object=self.__map_create_tenants(tenants),
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
                        expected=[
                            str,
                            Tenant,
                            Sequence[Union[str, Tenant]],
                        ],
                        name="tenants",
                        value=tenants,
                    )
                ]
            )

        tenant_names: List[str] = []
        if isinstance(tenants, str) or isinstance(tenants, Tenant):
            tenant_names = [tenants.name if isinstance(tenants, Tenant) else tenants]
        else:
            for tenant in tenants:
                tenant_names.append(tenant.name if isinstance(tenant, Tenant) else tenant)

        path = "/schema/" + self._name + "/tenants"
        await self._connection.delete(
            path=path,
            weaviate_object=tenant_names,
            error_msg=f"Collection tenants may not have been deleted for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self._name}"
            ),
        )

    async def __get_with_rest(self) -> Dict[str, TenantOutputType]:
        path = "/schema/" + self._name + "/tenants"
        response = await self._connection.get(
            path=path,
            error_msg=f"Could not get collection tenants for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Get collection tenants for {self._name}"
            ),
        )

        tenant_resp: List[Dict[str, Any]] = response.json()
        for tenant in tenant_resp:
            tenant["activityStatusInternal"] = tenant["activityStatus"]
            del tenant["activityStatus"]
        return {tenant["name"]: TenantOutput(**tenant) for tenant in tenant_resp}

    async def __get_with_grpc(
        self, tenants: Optional[Sequence[Union[str, Tenant]]] = None
    ) -> Dict[str, TenantOutputType]:
        response = await self._grpc.get(
            names=(
                [tenant.name if isinstance(tenant, Tenant) else tenant for tenant in tenants]
                if tenants is not None
                else tenants
            )
        )

        return {
            tenant.name: Tenant(
                name=tenant.name,
                activity_status=self._grpc.map_activity_status(tenant.activity_status),
            )
            for tenant in response.tenants
        }

    def __map_create_tenant(self, tenant: TenantCreateInputType) -> TenantCreate:
        if isinstance(tenant, str):
            return TenantCreate(name=tenant)
        if isinstance(tenant, Tenant):
            if tenant.activity_status not in [
                TenantActivityStatus.ACTIVE,
                TenantActivityStatus.INACTIVE,
            ]:
                raise WeaviateInvalidInputError(
                    f"Tenant activity status must be either 'ACTIVE' or 'INACTIVE'. Other statuses are read-only and cannot be set. Tenant: {tenant.name} had status: {tenant.activity_status}"
                )
            activity_status = TenantCreateActivityStatus(tenant.activity_status)
            return TenantCreate(name=tenant.name, activity_status=activity_status)
        return tenant

    def __map_update_tenant(self, tenant: TenantUpdateInputType) -> TenantUpdate:
        if isinstance(tenant, Tenant):
            if tenant.activity_status not in [
                TenantActivityStatus.ACTIVE,
                TenantActivityStatus.INACTIVE,
                TenantActivityStatus.OFFLOADED,
            ]:
                raise WeaviateInvalidInputError(
                    f"Tenant activity status must be one of 'ACTIVE', 'INACTIVE' or 'OFFLOADED'. Other statuses are read-only and cannot be set. Tenant: {tenant.name} had status: {tenant.activity_status}"
                )
            activity_status = TenantUpdateActivityStatus(tenant.activity_status)
            return TenantUpdate(name=tenant.name, activity_status=activity_status)
        return tenant

    def __map_create_tenants(
        self, tenants: Union[str, Tenant, TenantCreate, Sequence[Union[str, Tenant, TenantCreate]]]
    ) -> List[dict]:
        if (
            isinstance(tenants, str)
            or isinstance(tenants, Tenant)
            or isinstance(tenants, TenantCreate)
        ):
            return [self.__map_create_tenant(tenants).model_dump()]
        else:
            return [self.__map_create_tenant(tenant).model_dump() for tenant in tenants]

    def __map_update_tenants(
        self, tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]]
    ) -> List[List[dict]]:
        if (
            isinstance(tenants, str)
            or isinstance(tenants, Tenant)
            or isinstance(tenants, TenantUpdate)
        ):
            return [[self.__map_update_tenant(tenants).model_dump()]]
        else:
            batches = ceil(len(tenants) / UPDATE_TENANT_BATCH_SIZE)
            return [
                [
                    self.__map_update_tenant(tenants[i + b * UPDATE_TENANT_BATCH_SIZE]).model_dump()
                    for i in range(
                        min(len(tenants) - b * UPDATE_TENANT_BATCH_SIZE, UPDATE_TENANT_BATCH_SIZE)
                    )
                ]
                for b in range(batches)
            ]

    async def get(self) -> Dict[str, TenantOutputType]:
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
        self._connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_names' method")
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Sequence[Union[str, Tenant]]],
                    name="names",
                    value=tenants,
                )
            )
        return await self.__get_with_grpc(tenants=tenants)

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
        self._connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_name' method")
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(expected=[Union[str, Tenant]], name="tenant", value=tenant)
            )
        response = await self._grpc.get(
            names=[tenant.name if isinstance(tenant, Tenant) else tenant]
        )
        if len(response.tenants) == 0:
            return None
        return Tenant(
            name=response.tenants[0].name,
            activity_status=self._grpc.map_activity_status(response.tenants[0].activity_status),
        )

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
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Tenant, TenantUpdate, Sequence[Union[Tenant, TenantUpdate]]],
                    name="tenants",
                    value=tenants,
                )
            )

        path = "/schema/" + self._name + "/tenants"
        for mapped_tenants in self.__map_update_tenants(tenants):
            await self._connection.put(
                path=path,
                weaviate_object=mapped_tenants,
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
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[str, Tenant, Sequence[Union[str, Tenant]]],
                    name="tenant",
                    value=tenant,
                )
            )

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

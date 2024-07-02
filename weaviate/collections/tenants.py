from typing import Any, Dict, List, Optional, Sequence, Union

from weaviate.collections.classes.tenants import (
    Tenant,
    TenantInput,
    TenantActivityStatus,
    TenantActivityStatusInput,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.grpc.tenants import _TenantsGRPC
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.validator import _validate_input, _ValidateArgument

from weaviate.connect.v4 import _ExpectedStatusCodes


TenantInputType = Union[str, Tenant, TenantInput]
TenantOutputType = Tenant


class _Tenants:
    """Represents all the CRUD methods available on a collection's multi-tenancy specification within Weaviate.

    The collection must have been created with multi-tenancy enabled in order to use any of these methods. This class
    should not be instantiated directly, but is available as a property of the `Collection` class under
    the `collection.tenants` class attribute.
    """

    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel] = None,
        validate_arguments: bool = True,
    ) -> None:
        self.__connection = connection
        self.__name = name
        self.__grpc = _TenantsGRPC(
            connection=connection,
            name=name,
            consistency_level=consistency_level,
        )
        self.__validate_arguments = validate_arguments

    def create(self, tenants: Union[TenantInputType, Sequence[TenantInputType]]) -> None:
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
        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        expected=[
                            str,
                            Tenant,
                            TenantInput,
                            Sequence[Union[str, Tenant, TenantInput]],
                        ],
                        name="tenants",
                        value=tenants,
                    )
                ]
            )

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.post(
            path=path,
            weaviate_object=self.__map_input_tenants(tenants),
            error_msg=f"Collection tenants may not have been added properly for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Add collection tenants for {self.__name}"
            ),
        )

    def remove(self, tenants: Union[TenantInputType, Sequence[TenantInputType]]) -> None:
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
        if self.__validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        expected=[
                            str,
                            Tenant,
                            TenantInput,
                            Sequence[Union[str, Tenant, TenantInput]],
                        ],
                        name="tenants",
                        value=tenants,
                    )
                ]
            )

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.delete(
            path=path,
            weaviate_object=self.__map_input_tenant_names(tenants),
            error_msg=f"Collection tenants may not have been deleted for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self.__name}"
            ),
        )

    def __get_with_rest(self) -> Dict[str, TenantOutputType]:
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

    def __get_with_grpc(
        self, tenants: Optional[Sequence[TenantInputType]] = None
    ) -> Dict[str, TenantOutputType]:
        response = self.__grpc.get(
            names=(
                [
                    (
                        tenant.name
                        if isinstance(tenant, Tenant) or isinstance(tenant, TenantInput)
                        else tenant
                    )
                    for tenant in tenants
                ]
                if tenants is not None
                else tenants
            )
        )

        return {
            tenant.name: Tenant(
                name=tenant.name,
                activity_status=self.__grpc.map_activity_status(tenant.activity_status),
            )
            for tenant in response.tenants
        }

    def __map_input_tenant(self, tenant: TenantInputType) -> TenantInput:
        if isinstance(tenant, str):
            return TenantInput(name=tenant)
        if isinstance(tenant, Tenant):
            if tenant.activity_status in [
                TenantActivityStatus.FREEZING,
                TenantActivityStatus.UNFROZEN,
                TenantActivityStatus.UNFREEZING,
            ]:
                raise WeaviateInvalidInputError(
                    f"Tenant activity status must be one of 'HOT', 'COLD' or 'FROZEN'. Other statuses are read-only and cannot be set. Tenant: {tenant.name} had status: {tenant.activity_status}"
                )
            activity_status = TenantActivityStatusInput(tenant.activity_status)
            return TenantInput(name=tenant.name, activity_status=activity_status)
        if isinstance(tenant, TenantInput):
            return tenant

    def __map_input_tenants(
        self, tenant: Union[TenantInputType, Sequence[TenantInputType]]
    ) -> List[dict]:
        if isinstance(tenant, str) or isinstance(tenant, Tenant) or isinstance(tenant, TenantInput):
            return [self.__map_input_tenant(tenant).model_dump()]
        return [self.__map_input_tenant(t).model_dump() for t in tenant]

    def __map_input_tenant_names(
        self, tenant: Union[TenantInputType, Sequence[TenantInputType]]
    ) -> List[str]:
        if isinstance(tenant, str) or isinstance(tenant, Tenant) or isinstance(tenant, TenantInput):
            return [self.__map_input_tenant(tenant).name]
        return [self.__map_input_tenant(t).name for t in tenant]

    def get(self) -> Dict[str, TenantOutputType]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        if self.__connection._weaviate_version.supports_tenants_get_grpc:
            return self.__get_with_grpc()
        else:
            return self.__get_with_rest()

    def get_by_names(self, tenants: Sequence[TenantInputType]) -> Dict[str, TenantOutputType]:
        """Return named tenants currently associated with a collection in Weaviate.

        If the tenant does not exist, it will not be included in the response.
        If no names are provided, all tenants will be returned.
        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `tenant`
                Sequence of tenant names of wvc.tenants.Tenant objects to retrieve. To retrieve all tenants, use the `get` method.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        self.__connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_names' method")
        if self.__validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Sequence[Union[str, Tenant, TenantInput]]],
                    name="names",
                    value=tenants,
                )
            )
        return self.__get_with_grpc(tenants=tenants)

    def get_by_name(self, tenant: TenantInputType) -> Optional[TenantOutputType]:
        """Return a specific tenant associated with a collection in Weaviate.

        If the tenant does not exist, `None` will be returned.

        The collection must have been created with multi-tenancy enabled.

        Arguments:
            `name`
                The name of the tenant to retrieve.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to Weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a non-OK status.
        """
        self.__connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_name' method")
        if self.__validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Union[str, Tenant, TenantInput]], name="tenant", value=tenant
                )
            )
        response = self.__grpc.get(
            names=[
                (
                    tenant.name
                    if isinstance(tenant, Tenant) or isinstance(tenant, TenantInput)
                    else tenant
                )
            ]
        )
        if len(response.tenants) == 0:
            return None
        return Tenant(
            name=response.tenants[0].name,
            activity_status=self.__grpc.map_activity_status(response.tenants[0].activity_status),
        )

    def update(
        self, tenants: Union[Tenant, TenantInput, Sequence[Union[Tenant, TenantInput]]]
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
        if self.__validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Tenant, TenantInput, Sequence[Union[Tenant, TenantInput]]],
                    name="tenants",
                    value=tenants,
                )
            )

        path = "/schema/" + self.__name + "/tenants"
        self.__connection.put(
            path=path,
            weaviate_object=self.__map_input_tenants(tenants),
            error_msg=f"Collection tenants may not have been updated properly for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Update collection tenants for {self.__name}"
            ),
        )

    def exists(self, tenant: TenantInputType) -> bool:
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
        self.__connection._weaviate_version.check_is_at_least_1_25_0("The 'exists' method")
        if self.__validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[str, Tenant, TenantInput, Sequence[Union[str, Tenant, TenantInput]]],
                    name="tenant",
                    value=tenant,
                )
            )

        tenant_name = (
            tenant.name if isinstance(tenant, Tenant) or isinstance(tenant, TenantInput) else tenant
        )

        path = "/schema/" + self.__name + "/tenants/" + tenant_name
        response = self.__connection.head(
            path=path,
            error_msg=f"Could not check if tenant exists for {self.__name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404], error=f"Check if tenant exists for {self.__name}"
            ),  # allow 404 to perform bool check on response code
        )
        return response.status_code == 200

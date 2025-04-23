import asyncio
from math import ceil
from typing import Any, Dict, Generic, List, Optional, Sequence, Union

from httpx import Response

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
from weaviate.collections.tenants.types import (
    TenantCreateInputType,
    TenantUpdateInputType,
    TenantOutputType,
)
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, ConnectionType
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import tenants_pb2
from weaviate.validator import _validate_input, _ValidateArgument


UPDATE_TENANT_BATCH_SIZE = 100


class _TenantsExecutor(Generic[ConnectionType]):
    def __init__(
        self,
        connection: ConnectionType,
        name: str,
        validate_arguments: bool = True,
    ) -> None:
        self._connection = connection
        self._name = name
        self._grpc = _TenantsGRPC(
            weaviate_version=connection._weaviate_version,
            name=name,
        )
        self._validate_arguments = validate_arguments

    def create(
        self,
        tenants: Union[TenantCreateInputType, Sequence[TenantCreateInputType]],
    ) -> executor.Result[None]:
        """Create the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Args:
            tenants: A tenant name, `wvc.config.tenants.Tenant`, `wvc.config.tenants.TenantCreateInput` object, or a list of tenants names
                and/or `wvc.config.tenants.Tenant` objects to add to the given collection.
                If a string is provided, the tenant will be added with the default activity status of `HOT`.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If `tenants` is not a list of `wvc.Tenant` objects.
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

        def resp(res: Response) -> None:
            return None

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object=self.__map_create_tenants(tenants),
            error_msg=f"Collection tenants may not have been added properly for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Add collection tenants for {self._name}"
            ),
        )

    def remove(
        self,
        tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]],
    ) -> executor.Result[None]:
        """Remove the specified tenants from a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Args:
            tenants: A tenant name, `wvc.config.tenants.Tenant` object, or a list of tenants names
                and/or `wvc.config.tenants.Tenant` objects to remove from the given class.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If `tenants` is not a list of strings.
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

        def resp(res: Response) -> None:
            return None

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=path,
            weaviate_object=tenant_names,
            error_msg=f"Collection tenants may not have been deleted for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self._name}"
            ),
        )

    def __get_with_rest(
        self,
    ) -> executor.Result[Dict[str, TenantOutputType]]:
        path = "/schema/" + self._name + "/tenants"

        def resp(res: Response) -> Dict[str, TenantOutputType]:
            tenant_resp: List[Dict[str, Any]] = res.json()
            for tenant in tenant_resp:
                tenant["activityStatusInternal"] = tenant["activityStatus"]
                del tenant["activityStatus"]
            return {tenant["name"]: TenantOutput(**tenant) for tenant in tenant_resp}

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get collection tenants for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Get collection tenants for {self._name}"
            ),
        )

    def __get_with_grpc(
        self, *, tenants: Optional[Sequence[Union[str, Tenant]]] = None
    ) -> executor.Result[Dict[str, TenantOutputType]]:
        names = (
            [tenant.name if isinstance(tenant, Tenant) else tenant for tenant in tenants]
            if tenants is not None
            else tenants
        )
        request = tenants_pb2.TenantsGetRequest(
            collection=self._name,
            names=tenants_pb2.TenantNames(values=names) if names is not None else None,
        )

        def resp(res: tenants_pb2.TenantsGetReply) -> Dict[str, TenantOutputType]:
            return {
                tenant.name: TenantOutput(
                    name=tenant.name,
                    activity_status=self._grpc.map_activity_status(tenant.activity_status),
                )
                for tenant in res.tenants
            }

        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_tenants_get,
            request=request,
        )

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
        if isinstance(tenants, Tenant) or isinstance(tenants, TenantUpdate):
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

    def get(self) -> executor.Result[Dict[str, TenantOutputType]]:
        """Return all tenants currently associated with a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """

        def resp(res: Dict[str, TenantOutputType]) -> Dict[str, TenantOutputType]:
            return res

        return executor.execute(
            response_callback=resp,
            method=(
                self.__get_with_grpc
                if self._connection._weaviate_version.supports_tenants_get_grpc
                else self.__get_with_rest
            ),
        )

    def get_by_names(
        self, tenants: Sequence[Union[str, Tenant]]
    ) -> executor.Result[Dict[str, TenantOutputType]]:
        """Return named tenants currently associated with a collection in Weaviate.

        If the tenant does not exist, it will not be included in the response.
        If no names are provided, all tenants will be returned.
        The collection must have been created with multi-tenancy enabled.

        Args:
            tenants: Sequence of tenant names of wvc.tenants.Tenant objects to retrieve. To retrieve all tenants, use the `get` method.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
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
        return self.__get_with_grpc(tenants=tenants)

    def get_by_name(
        self, tenant: Union[str, Tenant]
    ) -> executor.Result[Optional[TenantOutputType]]:
        """Return a specific tenant associated with a collection in Weaviate.

        If the tenant does not exist, `None` will be returned.

        The collection must have been created with multi-tenancy enabled.

        Args:
            tenant: The tenant to retrieve.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
        """
        self._connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_name' method")
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(expected=[Union[str, Tenant]], name="tenant", value=tenant)
            )
        tenant_name = tenant.name if isinstance(tenant, Tenant) else tenant
        if self._connection._weaviate_version.is_lower_than(1, 28, 0):
            # For Weaviate versions < 1.28.0, we need to use the gRPC API
            # such versions don't have RBAC so the filtering issue doesn't exist therein
            def resp_grpc(res: Dict[str, TenantOutputType]) -> Optional[TenantOutputType]:
                return res.get(tenant_name)

            return executor.execute(
                response_callback=resp_grpc,
                method=self.__get_with_grpc,
                tenants=[tenant_name],
            )

        # For Weaviate versions >= 1.28.0, we need to use the REST API
        # as the gRPC API filters out tenants that are not accessible to the user
        # due to RBAC requirements
        def resp_rest(res: Response) -> Optional[TenantOutputType]:
            if res.status_code == 404:
                return None
            return Tenant(**res.json())

        return executor.execute(
            response_callback=resp_rest,
            method=self._connection.get,
            path=f"/schema/{self._name}/tenants/{tenant_name}",
            error_msg=f"Could not get tenant {tenant_name} for collection {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404], error=f"Get tenant {tenant_name} for collection {self._name}"
            ),
        )

    def __update(
        self,
        tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]],
    ) -> executor.Result[None]:
        path = "/schema/" + self._name + "/tenants"
        if isinstance(self._connection, ConnectionAsync):

            async def _execute() -> None:
                await asyncio.gather(
                    *[
                        executor.aresult(
                            self._connection.put(
                                path=path,
                                weaviate_object=mapped_tenants,
                                error_msg=f"Collection tenants may not have been updated properly for {self._name}",
                                status_codes=_ExpectedStatusCodes(
                                    ok_in=200, error=f"Update collection tenants for {self._name}"
                                ),
                            )
                        )
                        for mapped_tenants in self.__map_update_tenants(tenants)
                    ]
                )

            return _execute()
        for mapped_tenants in self.__map_update_tenants(tenants):
            self._connection.put(
                path=path,
                weaviate_object=mapped_tenants,
                error_msg=f"Collection tenants may not have been updated properly for {self._name}",
                status_codes=_ExpectedStatusCodes(
                    ok_in=200, error=f"Update collection tenants for {self._name}"
                ),
            )

    def update(
        self,
        tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]],
    ) -> executor.Result[None]:
        """Update the specified tenants for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Args:
            tenants: A tenant name, `wvc.config.tenants.Tenant` object, or a list of tenants names
                and/or `wvc.config.tenants.Tenant` objects to update for the given collection.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
            weaviate.exceptions.WeaviateInvalidInputError: If `tenants` is not a list of `wvc.Tenant` objects.
        """
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Tenant, TenantUpdate, Sequence[Union[Tenant, TenantUpdate]]],
                    name="tenants",
                    value=tenants,
                )
            )
        return self.__update(tenants=tenants)

    def exists(self, tenant: Union[str, Tenant]) -> executor.Result[bool]:
        """Check if a tenant exists for a collection in Weaviate.

        The collection must have been created with multi-tenancy enabled.

        Args:
            tenant: Tenant name or `wvc.config.tenants.Tenant` object to check for existence.

        Returns:
            `True` if the tenant exists, `False` otherwise.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to Weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a non-OK status.
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

        def resp(res: Response) -> bool:
            return res.status_code == 200

        tenant_name = tenant.name if isinstance(tenant, Tenant) else tenant
        path = "/schema/" + self._name + "/tenants/" + tenant_name
        return executor.execute(
            response_callback=resp,
            method=self._connection.head,
            path=path,
            error_msg=f"Could not check if tenant exists for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404], error=f"Check if tenant exists for {self._name}"
            ),  # allow 404 to perform bool check on response code
        )

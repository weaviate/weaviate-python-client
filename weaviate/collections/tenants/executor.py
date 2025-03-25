import asyncio
from math import ceil
from typing import Any, Awaitable, Dict, List, Optional, Sequence, Union, overload

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
from weaviate.connect.executor import aresult, execute, ExecutorResult
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, Connection, ConnectionSync
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import tenants_pb2
from weaviate.util import _ServerVersion
from weaviate.validator import _validate_input, _ValidateArgument

TenantCreateInputType = Union[str, Tenant, TenantCreate]
TenantUpdateInputType = Union[Tenant, TenantUpdate]
TenantOutputType = Tenant

UPDATE_TENANT_BATCH_SIZE = 100


class _TenantsExecutor:
    def __init__(
        self,
        weaviate_version: _ServerVersion,
        name: str,
        validate_arguments: bool = True,
    ) -> None:
        self._weaviate_version = weaviate_version
        self._name = name
        self._grpc = _TenantsGRPC(
            weaviate_version=weaviate_version,
            name=name,
        )
        self._validate_arguments = validate_arguments

    def create(
        self,
        connection: Connection,
        *,
        tenants: Union[TenantCreateInputType, Sequence[TenantCreateInputType]],
    ) -> ExecutorResult[None]:
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

        return execute(
            response_callback=resp,
            method=connection.post,
            path=path,
            weaviate_object=self.__map_create_tenants(tenants),
            error_msg=f"Collection tenants may not have been added properly for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Add collection tenants for {self._name}"
            ),
        )

    def remove(
        self,
        connection: Connection,
        *,
        tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]],
    ) -> ExecutorResult[None]:
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

        return execute(
            response_callback=resp,
            method=connection.delete,
            path=path,
            weaviate_object=tenant_names,
            error_msg=f"Collection tenants may not have been deleted for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Delete collection tenants for {self._name}"
            ),
        )

    def __get_with_rest(
        self, connection: Connection
    ) -> ExecutorResult[Dict[str, TenantOutputType]]:
        path = "/schema/" + self._name + "/tenants"

        def resp(res: Response) -> Dict[str, TenantOutputType]:
            tenant_resp: List[Dict[str, Any]] = res.json()
            for tenant in tenant_resp:
                tenant["activityStatusInternal"] = tenant["activityStatus"]
                del tenant["activityStatus"]
            return {tenant["name"]: TenantOutput(**tenant) for tenant in tenant_resp}

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg=f"Could not get collection tenants for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=200, error=f"Get collection tenants for {self._name}"
            ),
        )

    def __get_with_grpc(
        self, connection: Connection, *, tenants: Optional[Sequence[Union[str, Tenant]]] = None
    ) -> ExecutorResult[Dict[str, TenantOutputType]]:
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

        return execute(
            response_callback=resp,
            method=connection.grpc_tenants_get,
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

    def get(self, connection: ConnectionAsync) -> ExecutorResult[Dict[str, TenantOutputType]]:
        def resp(res: Dict[str, TenantOutputType]) -> Dict[str, TenantOutputType]:
            return res

        return execute(
            response_callback=resp,
            method=(
                self.__get_with_grpc
                if self._weaviate_version.supports_tenants_get_grpc
                else self.__get_with_rest
            ),
            connection=connection,
        )

    def get_by_names(
        self, connection: Connection, *, tenants: Sequence[Union[str, Tenant]]
    ) -> ExecutorResult[Dict[str, TenantOutputType]]:
        connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_names' method")
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Sequence[Union[str, Tenant]]],
                    name="names",
                    value=tenants,
                )
            )
        return self.__get_with_grpc(connection=connection, tenants=tenants)

    def get_by_name(
        self, connection: Connection, *, tenant: Union[str, Tenant]
    ) -> ExecutorResult[Optional[TenantOutputType]]:
        connection._weaviate_version.check_is_at_least_1_25_0("The 'get_by_name' method")
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(expected=[Union[str, Tenant]], name="tenant", value=tenant)
            )

        def resp(res: Dict[str, TenantOutputType]) -> Optional[TenantOutputType]:
            return res.get(tenant.name if isinstance(tenant, Tenant) else tenant)

        return execute(
            response_callback=resp,
            method=self.get_by_names,
            connection=connection,
            tenants=[tenant],
        )

    @overload
    def __update(
        self,
        connection: ConnectionAsync,
        *,
        tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]],
    ) -> Awaitable[None]: ...

    @overload
    def __update(
        self,
        connection: ConnectionSync,
        *,
        tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]],
    ) -> None: ...

    def __update(
        self,
        connection: Connection,
        *,
        tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]],
    ) -> ExecutorResult[None]:
        path = "/schema/" + self._name + "/tenants"
        if isinstance(connection, ConnectionAsync):

            async def _execute() -> None:
                await asyncio.gather(
                    *[
                        aresult(
                            connection.put(
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
            connection.put(
                path=path,
                weaviate_object=mapped_tenants,
                error_msg=f"Collection tenants may not have been updated properly for {self._name}",
                status_codes=_ExpectedStatusCodes(
                    ok_in=200, error=f"Update collection tenants for {self._name}"
                ),
            )

    def update(
        self,
        connection: Connection,
        *,
        tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]],
    ) -> ExecutorResult[None]:
        if self._validate_arguments:
            _validate_input(
                _ValidateArgument(
                    expected=[Tenant, TenantUpdate, Sequence[Union[Tenant, TenantUpdate]]],
                    name="tenants",
                    value=tenants,
                )
            )
        return self.__update(connection, tenants=tenants)

    def exists(self, connection: Connection, *, tenant: Union[str, Tenant]) -> ExecutorResult[bool]:
        connection._weaviate_version.check_is_at_least_1_25_0("The 'exists' method")
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
        return execute(
            response_callback=resp,
            method=connection.head,
            path=path,
            error_msg=f"Could not check if tenant exists for {self._name}",
            status_codes=_ExpectedStatusCodes(
                ok_in=[200, 404], error=f"Check if tenant exists for {self._name}"
            ),  # allow 404 to perform bool check on response code
        )

import asyncio
import json
from typing import Awaitable, Dict, List, Optional, Sequence, Union, cast, overload

from httpx import Response

from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync, ConnectionSync
from weaviate.connect.executor import ExecutorResult, execute, raise_exception
from weaviate.rbac.models import (
    _Permission,
    PermissionsOutputType,
    PermissionsInputType,
    Role,
    WeaviateRole,
)


def _flatten_permissions(
    permissions: Union[PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]]
) -> List[_Permission]:
    if isinstance(permissions, _Permission):
        return [permissions]
    flattened_permissions: List[_Permission] = []
    for permission in permissions:
        if isinstance(permission, _Permission):
            flattened_permissions.append(permission)
        else:
            flattened_permissions.extend(permission)
    return flattened_permissions


class _RolesExecutor:
    def list_all(self, connection: ConnectionAsync) -> Awaitable[Dict[str, Role]]:
        path = "/authz/roles"

        def resp(res: Response) -> Dict[str, Role]:
            return {role["name"]: Role._from_weaviate_role(role) for role in res.json()}

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles"),
        )

    def get_current_roles(self, connection: ConnectionAsync) -> Awaitable[List[WeaviateRole]]:
        path = "/authz/users/own-roles"

        return execute(
            response_callback=lambda res: cast(List[WeaviateRole], res.json()),
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    def exists(self, connection: ConnectionAsync, *, role_name: str) -> Awaitable[bool]:
        path = f"/authz/roles/{role_name}"

        return execute(
            response_callback=lambda res: res.status_code == 200,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg=f"Could not get role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get role"),
        )

    def get(self, connection: ConnectionAsync, *, role_name: str) -> Awaitable[Optional[Role]]:
        path = f"/authz/roles/{role_name}"

        def resp(res: Response) -> Optional[Role]:
            if res.status_code == 404:
                return None
            return Role._from_weaviate_role(cast(WeaviateRole, res.json()))

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg=f"Could not get role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get role"),
        )

    def create(
        self, connection: ConnectionAsync, *, permissions: PermissionsInputType, role_name: str
    ) -> Awaitable[Role]:
        path = "/authz/roles"

        perms = []
        for perm in _flatten_permissions(permissions):
            perms.extend(perm._to_weaviate())

        role: WeaviateRole = {
            "name": role_name,
            "permissions": perms,
        }

        return execute(
            response_callback=lambda res: Role._from_weaviate_role(role),
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object=role,
            error_msg=f"Could not create role: {json.dumps(role)}",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create role"),
        )

    def get_assigned_user_ids(
        self, connection: ConnectionAsync, *, name: str
    ) -> Awaitable[List[str]]:
        path = f"/authz/roles/{name}/users"

        return execute(
            response_callback=lambda res: cast(List[str], res.json()),
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg=f"Could not get users of role {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get users of role"),
        )

    def delete_role(self, connection: ConnectionAsync, *, role_name: str) -> Awaitable[None]:
        path = f"/authz/roles/{role_name}"

        return execute(
            response_callback=lambda res: None,
            exception_callback=raise_exception,
            method=connection.delete,
            path=path,
            error_msg=f"Could not delete role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[204], error="Delete role"),
        )

    def add_permissions(
        self, connection: ConnectionAsync, *, permissions: PermissionsInputType, role_name: str
    ) -> Awaitable[None]:
        path = f"/authz/roles/{role_name}/add-permissions"

        if isinstance(permissions, _Permission):
            permissions = [permissions]

        perms = []
        for perm in _flatten_permissions(permissions):
            perms.extend(perm._to_weaviate())

        return execute(
            response_callback=lambda res: None,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object={"permissions": permissions},
            error_msg="Could not add permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Add permissions"),
        )

    def remove_permissions(
        self, connection: ConnectionAsync, *, permissions: PermissionsInputType, role_name: str
    ) -> Awaitable[None]:
        path = f"/authz/roles/{role_name}/remove-permissions"

        if isinstance(permissions, _Permission):
            permissions = [permissions]

        perms = []
        for perm in _flatten_permissions(permissions):
            perms.extend(perm._to_weaviate())

        return execute(
            response_callback=lambda res: None,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object={"permissions": permissions},
            error_msg="Could not remove permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Remove permissions"),
        )

    def has_permissions(
        self,
        connection: ConnectionAsync,
        *,
        permissions: Union[
            PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]
        ],
        role: str,
    ) -> Awaitable[bool]:
        path = f"/authz/roles/{role}/has-permission"

        perms = []
        for perm in _flatten_permissions(permissions):
            perms.extend(perm._to_weaviate())

        if isinstance(connection, ConnectionAsync):

            async def execute() -> bool:
                call = lambda permission: connection.post(
                    path=path,
                    weaviate_object=permission,
                    error_msg="Could not check permission",
                    status_codes=_ExpectedStatusCodes(ok_in=[200], error="Check permission"),
                )
                return all(await asyncio.gather(*[call(permission) for permission in perms]))

            return execute()

        call = lambda permission: connection.post(
            path=path,
            weaviate_object=permission,
            error_msg="Could not check permission",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Check permission"),
        )
        return all(call(permission) for permission in perms)

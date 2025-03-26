import asyncio
import json
from typing import Dict, List, Optional, Sequence, Union, cast

from httpx import Response

from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync
from weaviate.connect.executor import ExecutorResult, aresult, execute, raise_exception, result
from weaviate.rbac.models import (
    _Permission,
    PermissionsOutputType,
    PermissionsInputType,
    Role,
    UserAssignment,
    UserTypes,
    WeaviatePermission,
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
    def list_all(self, connection: Connection) -> ExecutorResult[Dict[str, Role]]:
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

    def get_current_roles(self, connection: Connection) -> ExecutorResult[List[WeaviateRole]]:
        path = "/authz/users/own-roles"

        def resp(res: Response) -> List[WeaviateRole]:
            return cast(List[WeaviateRole], res.json())

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    def exists(self, role_name: str, *, connection: Connection) -> ExecutorResult[bool]:
        path = f"/authz/roles/{role_name}"

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg=f"Could not get role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get role"),
        )

    def get(self, role_name: str, *, connection: Connection) -> ExecutorResult[Optional[Role]]:
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
        self, *, connection: Connection, permissions: PermissionsInputType, role_name: str
    ) -> ExecutorResult[Role]:
        path = "/authz/roles"

        perms = []
        for perm in _flatten_permissions(permissions):
            perms.extend(perm._to_weaviate())

        role: WeaviateRole = {
            "name": role_name,
            "permissions": perms,
        }

        def resp(res: Response) -> Role:
            return Role._from_weaviate_role(role)

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object=role,
            error_msg=f"Could not create role: {json.dumps(role)}",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create role"),
        )

    def get_user_assignments(
        self, role_name: str, *, connection: Connection
    ) -> ExecutorResult[List[UserAssignment]]:
        path = f"/authz/roles/{role_name}/user-assignments"

        def resp(res: Response) -> List[UserAssignment]:
            return [
                UserAssignment(
                    user_id=assignment["userId"], user_type=UserTypes(assignment["userType"])
                )
                for assignment in res.json()
            ]

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg=f"Could not get users of role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get users of role"),
        )

    def get_assigned_user_ids(
        self, role_name: str, *, connection: Connection
    ) -> ExecutorResult[List[str]]:
        path = f"/authz/roles/{role_name}/users"

        def resp(res: Response) -> List[str]:
            return cast(List[str], res.json())

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.get,
            path=path,
            error_msg=f"Could not get users of role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get users of role"),
        )

    def delete(self, role_name: str, *, connection: Connection) -> ExecutorResult[None]:
        path = f"/authz/roles/{role_name}"

        def resp(res: Response) -> None:
            return None

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.delete,
            path=path,
            error_msg=f"Could not delete role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[204], error="Delete role"),
        )

    def add_permissions(
        self, connection: Connection, *, permissions: PermissionsInputType, role_name: str
    ) -> ExecutorResult[None]:
        path = f"/authz/roles/{role_name}/add-permissions"

        if isinstance(permissions, _Permission):
            permissions = [permissions]

        def resp(res: Response) -> None:
            return None

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object={
                "permissions": [
                    weav_perm
                    for perm in _flatten_permissions(permissions)
                    for weav_perm in perm._to_weaviate()
                ]
            },
            error_msg="Could not add permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Add permissions"),
        )

    def remove_permissions(
        self, connection: Connection, *, permissions: PermissionsInputType, role_name: str
    ) -> ExecutorResult[None]:
        path = f"/authz/roles/{role_name}/remove-permissions"

        if isinstance(permissions, _Permission):
            permissions = [permissions]

        def resp(res: Response) -> None:
            return None

        return execute(
            response_callback=resp,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object={
                "permissions": [
                    weav_perm
                    for perm in _flatten_permissions(permissions)
                    for weav_perm in perm._to_weaviate()
                ]
            },
            error_msg="Could not remove permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Remove permissions"),
        )

    def __has_permission(
        self, *, permission: WeaviatePermission, role: str, connection: Connection
    ) -> ExecutorResult[bool]:
        path = f"/authz/roles/{role}/has-permission"

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return execute(
            response_callback=resp,
            method=connection.post,
            path=path,
            weaviate_object=permission,
            error_msg="Could not check permission",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Check permission"),
        )

    def has_permissions(
        self,
        *,
        permissions: Union[
            PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]
        ],
        role: str,
        connection: Connection,
    ) -> ExecutorResult[bool]:
        if isinstance(connection, ConnectionAsync):

            async def execute() -> bool:
                return all(
                    await asyncio.gather(
                        *[
                            aresult(
                                self.__has_permission(
                                    connection=connection, permission=weav_perm, role=role
                                )
                            )
                            for permission in _flatten_permissions(permissions)
                            for weav_perm in permission._to_weaviate()
                        ]
                    )
                )

            return execute()

        return all(
            result(self.__has_permission(connection=connection, permission=weav_perm, role=role))
            for permission in _flatten_permissions(permissions)
            for weav_perm in permission._to_weaviate()
        )

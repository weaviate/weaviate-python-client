from dataclasses import dataclass
from typing import Any, Dict, Final, List, Literal, Optional, Union, cast

from httpx import Response

from weaviate.connect.executor import ExecutorResult, execute
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection
from weaviate.rbac.models import (
    Role,
    RoleBase,
    WeaviateDBUserRoleNames,
    UserTypes,
)

from weaviate.util import _decode_json_response_dict

USER_TYPE_DB: Final = "db"
USER_TYPE_OIDC: Final = "oidc"
USER_TYPE = Literal["db", "oidc"]


@dataclass
class OwnUser:
    user_id: str
    roles: Dict[str, Role]


@dataclass
class UserBase:
    user_id: str
    role_names: List[str]
    user_type: UserTypes


@dataclass
class UserDB(UserBase):
    user_type: UserTypes
    active: bool


@dataclass
class UserOIDC(UserBase):
    user_type: UserTypes = UserTypes.OIDC


class _BaseExecutor:
    def _get_roles_of_user(
        self,
        user_id: str,
        user_type: USER_TYPE,
        include_permissions: bool,
        *,
        connection: Connection,
    ) -> ExecutorResult[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        path = f"/authz/users/{user_id}/roles/{user_type}"

        def resp(res: Response) -> Union[Dict[str, Role], Dict[str, RoleBase]]:
            roles = res.json()
            if include_permissions:
                return {role["name"]: Role._from_weaviate_role(role) for role in roles}
            return {role["name"]: RoleBase(role["name"]) for role in roles}

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            params={"includeFullRoles": include_permissions},
            error_msg=f"Could not get roles of user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    def _get_roles_of_user_deprecated(
        self,
        user_id: str,
        *,
        connection: Connection,
    ) -> ExecutorResult[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        path = f"/authz/users/{user_id}/roles"

        def resp(res: Response) -> Union[Dict[str, Role], Dict[str, RoleBase]]:
            return {role["name"]: Role._from_weaviate_role(role) for role in res.json()}

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg=f"Could not get roles of user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    def _assign_roles_to_user(
        self,
        roles: List[str],
        user_id: str,
        user_type: Optional[USER_TYPE],
        *,
        connection: Connection,
    ) -> ExecutorResult[None]:
        path = f"/authz/users/{user_id}/assign"

        payload: Dict[str, Any] = {"roles": roles}
        if user_type is not None:
            payload["userType"] = user_type

        def resp(res: Response) -> None:
            pass

        return execute(
            response_callback=resp,
            method=connection.post,
            path=path,
            weaviate_object=payload,
            error_msg=f"Could not assign roles {roles} to user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    def _revoke_roles_from_user(
        self,
        roles: Union[str, List[str]],
        user_id: str,
        user_type: Optional[USER_TYPE],
        *,
        connection: Connection,
    ) -> ExecutorResult[None]:
        path = f"/authz/users/{user_id}/revoke"

        payload: Dict[str, Any] = {"roles": roles}
        if user_type is not None:
            payload["userType"] = user_type

        def resp(res: Response) -> None:
            pass

        return execute(
            response_callback=resp,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )


class _DeprecatedExecutor(_BaseExecutor):
    def get_my_user(self, connection: Connection) -> ExecutorResult[OwnUser]:
        path = "/users/own-info"

        def resp(res: Response) -> OwnUser:
            parsed = _decode_json_response_dict(res, "Get current user")
            assert parsed is not None
            # The API returns "username" for 1.29 instead of "user_id"
            user_id = parsed["username"] if "username" in parsed else parsed["user_id"]
            return OwnUser(
                user_id=user_id,
                roles=(
                    {role["name"]: Role._from_weaviate_role(role) for role in parsed["roles"]}
                    if parsed["roles"] is not None
                    else {}
                ),
            )

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    def get_assigned_roles(
        self, user_id: str, *, connection: Connection
    ) -> ExecutorResult[Dict[str, Role]]:
        # cast here because the deprecated method is only used in the deprecated class and this type is known
        return cast(
            Dict[str, Role], self._get_roles_of_user_deprecated(user_id, connection=connection)
        )

    def assign_roles(
        self, *, user_id: str, role_names: Union[str, List[str]], connection: Connection
    ) -> ExecutorResult[None]:
        return self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            None,
            connection=connection,
        )

    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]], connection: Connection
    ) -> ExecutorResult[None]:
        return self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            None,
            connection=connection,
        )


class _OIDCExecutor(_BaseExecutor):
    def get_assigned_roles(
        self, user_id: str, include_permissions: bool, *, connection: Connection
    ) -> ExecutorResult[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        return self._get_roles_of_user(
            user_id, USER_TYPE_OIDC, include_permissions, connection=connection
        )

    def assign_roles(
        self, *, user_id: str, role_names: Union[str, List[str]], connection: Connection
    ) -> ExecutorResult[None]:
        return self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_OIDC,
            connection=connection,
        )

    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]], connection: Connection
    ) -> ExecutorResult[None]:
        return self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_OIDC,
            connection=connection,
        )


class _DBExecutor(_BaseExecutor):
    def get_assigned_roles(
        self, user_id: str, include_permissions: bool, *, connection: Connection
    ) -> ExecutorResult[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        return self._get_roles_of_user(
            user_id, USER_TYPE_DB, include_permissions, connection=connection
        )

    def assign_roles(
        self, *, user_id: str, role_names: Union[str, List[str]], connection: Connection
    ) -> ExecutorResult[None]:
        return self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_DB,
            connection=connection,
        )

    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]], connection: Connection
    ) -> ExecutorResult[None]:
        return self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_DB,
            connection=connection,
        )

    def create(self, *, user_id: str, connection: Connection) -> ExecutorResult[str]:
        def resp(res: Response) -> str:
            resp = _decode_json_response_dict(res, "Create user")
            assert resp is not None
            return str(resp["apikey"])

        return execute(
            response_callback=resp,
            method=connection.post,
            path=f"/users/db/{user_id}",
            weaviate_object={},
            error_msg=f"Could not create user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create user"),
        )

    def delete(self, *, user_id: str, connection: Connection) -> ExecutorResult[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 204

        return execute(
            response_callback=resp,
            method=connection.delete,
            path=f"/users/db/{user_id}",
            error_msg=f"Could not delete user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="Delete user"),
        )

    def rotate_key(self, *, user_id: str, connection: Connection) -> ExecutorResult[str]:
        def resp(res: Response) -> str:
            resp = _decode_json_response_dict(res, "Rotate key")
            assert resp is not None
            return str(resp["apikey"])

        return execute(
            response_callback=resp,
            method=connection.post,
            path=f"/users/db/{user_id}/rotate-key",
            weaviate_object={},
            error_msg=f"Could not rotate key for user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Rotate key"),
        )

    def activate(self, *, user_id: str, connection: Connection) -> ExecutorResult[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 200

        return execute(
            response_callback=resp,
            method=connection.post,
            path=f"/users/db/{user_id}/activate",
            weaviate_object={},
            error_msg=f"Could not activate user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 409], error="Activate user"),
        )

    def deactivate(self, *, user_id: str, connection: Connection) -> ExecutorResult[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 200

        return execute(
            response_callback=resp,
            method=connection.post,
            path=f"/users/db/{user_id}/deactivate",
            weaviate_object={},
            error_msg=f"Could not deactivate user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 409], error="Deactivate user"),
        )

    def get(self, *, user_id: str, connection: Connection) -> ExecutorResult[Optional[UserDB]]:
        def resp(res: Response) -> Optional[UserDB]:
            if res.status_code == 404:
                return None
            parsed = _decode_json_response_dict(res, "Get user")
            assert parsed is not None
            return UserDB(
                user_id=parsed["userId"],
                role_names=parsed["roles"],
                active=parsed["active"],
                user_type=UserTypes(parsed["dbUserType"]),
            )

        return execute(
            response_callback=resp,
            method=connection.get,
            path=f"/users/db/{user_id}",
            error_msg=f"Could not get user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get user"),
        )

    def list_all(self, *, connection: Connection) -> ExecutorResult[List[UserDB]]:
        def resp(res: Response) -> List[UserDB]:
            parsed = _decode_json_response_dict(res, "Get user")
            assert parsed is not None
            return [
                UserDB(
                    user_id=user["userId"],
                    role_names=user["roles"],
                    active=user["active"],
                    user_type=UserTypes(user["dbUserType"]),
                )
                for user in cast(List[WeaviateDBUserRoleNames], parsed)
            ]

        return execute(
            response_callback=resp,
            method=connection.get,
            path="/users/db",
            error_msg="Could not list all users",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="list all users"),
        )

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Union, cast, Final, overload

from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.rbac.models import (
    Role,
    RoleBase,
    UserTypes,
    WeaviateDBUserRoleNames,
    WeaviateRole,
    WeaviateUser,
)

from weaviate.util import _decode_json_response_dict, _decode_json_response_list
from typing_extensions import deprecated

USER_TYPE_DB: Final = "db"
USER_TYPE_OIDC: Final = "oidc"


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


class _UsersInit:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection


class _UsersBase(_UsersInit):
    async def _get_roles_of_user(
        self, name: str, user_type: Literal["db", "oidc"], include_permissions: bool
    ) -> List[WeaviateRole]:
        path = f"/authz/users/{name}/roles/{user_type}"

        res = await self._connection.get(
            path,
            params={"includeFullRoles": include_permissions},
            error_msg=f"Could not get roles of user '{name}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )
        return cast(List[WeaviateRole], res.json())

    async def _assign_roles_to_user(
        self, roles: List[str], user_id: str, user_type: Optional[Literal["db", "oidc"]]
    ) -> None:
        path = f"/authz/users/{user_id}/assign"

        payload: Dict[str, Any] = {"roles": roles}
        if user_type is not None:
            payload["userType"] = user_type

        await self._connection.post(
            path,
            weaviate_object=payload,
            error_msg=f"Could not assign roles[{roles}] to user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    async def _revoke_roles_from_user(
        self, roles: List[str], user_id: str, user_type: Optional[Literal["db", "oidc"]]
    ) -> None:
        path = f"/authz/users/{user_id}/revoke"

        payload: Dict[str, Any] = {"roles": roles}
        if user_type is not None:
            payload["userType"] = user_type

        await self._connection.post(
            path,
            weaviate_object=payload,
            error_msg=f"Could not revoke roles [{roles}] from user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )

    async def _create_user(self, user_id: str) -> str:
        path = f"/users/db/{user_id}"
        resp = await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not create user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create user"),
        )
        resp_typed = _decode_json_response_dict(resp, "Create user")
        assert resp_typed is not None
        return str(resp_typed["apikey"])

    async def _delete_user(self, user_id: str) -> bool:
        path = f"/users/db/{user_id}"
        resp = await self._connection.delete(
            path,
            error_msg=f"Could not delete user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="Delete user"),
        )
        return resp.status_code == 204

    async def _rotate_key(self, user_id: str) -> str:
        path = f"/users/db/{user_id}/rotate-key"
        resp = await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not create user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="rotate key"),
        )
        resp_typed = _decode_json_response_dict(resp, "rotate key")
        assert resp_typed is not None
        return str(resp_typed["apikey"])

    async def _deactivate(self, user_id: str, revoke_key: bool) -> bool:
        path = f"/users/db/{user_id}/deactivate"
        resp = await self._connection.post(
            path,
            weaviate_object={"revoke_key": revoke_key},
            error_msg=f"Could not deactivate user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 409], error="deactivate key"),
        )
        return resp.status_code == 200

    async def _activate(self, user_id: str) -> bool:
        path = f"/users/db/{user_id}/activate"
        resp = await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not activate user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 409], error="activate key"),
        )
        return resp.status_code == 200

    async def _get_user(self, user_id: str) -> WeaviateDBUserRoleNames:
        path = f"/users/db/{user_id}"
        resp = await self._connection.get(
            path,
            error_msg=f"Could not get user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get user"),
        )
        parsed = _decode_json_response_dict(resp, "get user")
        assert parsed is not None
        return cast(WeaviateDBUserRoleNames, parsed)

    async def _list_all_users(self) -> List[WeaviateDBUserRoleNames]:
        path = "/users/db"
        resp = await self._connection.get(
            path,
            error_msg="Could not list all users",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="list all users"),
        )
        parsed = _decode_json_response_list(resp, "get user")
        assert parsed is not None
        return cast(List[WeaviateDBUserRoleNames], parsed)


class _UserDBAsync(_UsersBase):
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = ...
    ) -> Dict[str, RoleBase]: ...

    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True] = ...
    ) -> Dict[str, Role]: ...

    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> Union[Dict[str, Role], Dict[str, RoleBase]]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        roles = await self._get_roles_of_user(user_id, USER_TYPE_DB, include_permissions)
        if include_permissions:
            return {role["name"]: Role._from_weaviate_role(role) for role in roles}
        return {role["name"]: RoleBase(role["name"]) for role in roles}

    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names, user_id, USER_TYPE_DB
        )

    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names, user_id, USER_TYPE_DB
        )

    async def create(self, *, user_id: str) -> str:
        """Create a new db user.

        Args:
            user_id: The id of the new user.
        """
        return await self._create_user(user_id)

    async def delete(self, *, user_id: str) -> bool:
        """Delete a (dynamic) db user.

        Args:
            user_id: The id of the user to be deleted.
        """
        return await self._delete_user(user_id)

    async def rotate_key(self, *, user_id: str) -> str:
        """Rotate the key of a new db user.

        Args:
            user_id: The id of the user.
        """
        return await self._rotate_key(user_id)

    async def activate(self, *, user_id: str) -> bool:
        """Activate a deactivated user.

        Args:
            user_id: The id of the user.
        """
        return await self._activate(user_id)

    async def deactivate(self, *, user_id: str, revoke_key: bool = False) -> bool:
        """Deactivate an active user.

        Args:
            user_id: The id of the user.
            revoke_key: If True, the old key will be revoked and needs to be rotated.
        """
        return await self._deactivate(user_id, revoke_key)

    async def get(self, *, user_id: str) -> UserDB:
        """Get all information about an user.

        Args:
            user_id: The id of the user.
        """
        user = await self._get_user(user_id=user_id)

        return UserDB(
            user_id=user["userId"],
            role_names=user["roles"],
            active=user["active"],
            user_type=UserTypes(user["dbUserType"]),
        )

    async def list_all(self) -> List[UserDB]:
        """List all DB users."""
        users = await self._list_all_users()

        return [
            UserDB(
                user_id=user["userId"],
                role_names=user["roles"],
                active=user["active"],
                user_type=UserTypes(user["dbUserType"]),
            )
            for user in users
        ]


class _UserOIDCAsync(_UsersBase):
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = ...
    ) -> Dict[str, RoleBase]: ...

    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True] = ...
    ) -> Dict[str, Role]: ...

    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> Union[Dict[str, Role], Dict[str, RoleBase]]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        roles = await self._get_roles_of_user(user_id, USER_TYPE_OIDC, include_permissions)
        if include_permissions:
            return {role["name"]: Role._from_weaviate_role(role) for role in roles}
        return {role["name"]: RoleBase(role["name"]) for role in roles}

    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names, user_id, USER_TYPE_OIDC
        )

    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names, user_id, USER_TYPE_OIDC
        )


class _UsersWrapper:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection
        self._base = _UsersBase(connection)

    async def _get_current_user(self) -> WeaviateUser:
        path = "/users/own-info"

        res = await self._connection.get(
            path,
            error_msg="Could not own user info",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own user info"),
        )
        parsed = _decode_json_response_dict(res, "Get current user")
        assert parsed is not None
        # The API returns "username" for 1.29 instead of "user_id"
        if "username" in parsed:
            parsed["user_id"] = parsed["username"]
            parsed.pop("username")

        return cast(WeaviateUser, parsed)


class _UsersAsync(_UsersWrapper):
    def __init__(self, connection: ConnectionV4) -> None:
        super().__init__(connection)
        self.db = _UserDBAsync(connection)
        self.oidc = _UserOIDCAsync(connection)

        # this is needed so the sync version does not overwrite the async version
        self._db = _UserDBAsync(connection)
        self._oidc = _UserOIDCAsync(connection)

    async def get_my_user(self) -> OwnUser:
        """Get the currently authenticated user.

        Returns:
            A user object.
        """
        user = await self._get_current_user()
        return OwnUser(
            user_id=user["user_id"],
            roles=(
                {role["name"]: Role._from_weaviate_role(role) for role in user["roles"]}
                if user["roles"] is not None
                else {}
            ),
        )

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.get_assigned_roles` and/or `users.oidc.get_assigned_roles` instead."""
    )
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user for both OIDC as well as db users.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return {
            role["name"]: Role._from_weaviate_role(role)
            for role in await self.__get_roles_of_user_deprecated(user_id)
        }

    async def __get_roles_of_user_deprecated(self, name: str) -> List[WeaviateRole]:
        path = f"/authz/users/{name}/roles"

        res = await self._connection.get(
            path,
            error_msg=f"Could not get roles of user {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )
        return cast(List[WeaviateRole], res.json())

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.assign_roles` and/or `users.oidc.assign_roles` instead."""
    )
    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        if isinstance(role_names, str):
            role_names = [role_names]
        await self._base._assign_roles_to_user(user_id=user_id, roles=role_names, user_type=None)

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.revoke_roles` and/or `users.oidc.revoke_roles` instead."""
    )
    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        if isinstance(role_names, str):
            role_names = [role_names]
        await self._base._revoke_roles_from_user(user_id=user_id, roles=role_names, user_type=None)

from typing import Dict, List, Literal, Union, cast, Final

from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.rbac.models import (
    Role,
    User,
    UserDB,
    WeaviateDBUser,
    WeaviateRole,
    WeaviateUser,
)

from weaviate.util import _decode_json_response_dict
from typing_extensions import deprecated

USER_TYPE_DB: Final = "db"
USER_TYPE_OIDC: Final = "oidc"


class _UsersBase:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection

    async def _get_roles_of_user(
        self, name: str, user_type: Literal["db", "oidc"]
    ) -> List[WeaviateRole]:
        path = f"/authz/users/{name}/roles/{user_type}"

        res = await self._connection.get(
            path,
            error_msg=f"Could not get roles of user {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )
        return cast(List[WeaviateRole], res.json())

    async def _assign_roles_to_user(
        self, roles: List[str], user: str, user_type: Literal["db", "oidc"]
    ) -> None:
        path = f"/authz/users/{user}/assign"

        await self._connection.post(
            path,
            weaviate_object={"roles": roles, "userType": user_type},
            error_msg=f"Could not assign roles {roles} to user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    async def _revoke_roles_from_user(
        self, roles: List[str], user: str, user_type: Literal["db", "oidc"]
    ) -> None:
        path = f"/authz/users/{user}/revoke"

        await self._connection.post(
            path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )

    async def _create_user(self, user_id: str) -> str:
        path = f"/users/{user_id}"
        resp = await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not create user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create user"),
        )
        resp_typed = _decode_json_response_dict(resp, "Create user")
        assert resp_typed is not None
        return str(resp_typed["apikey"])

    async def _delete_user(self, user_id: str) -> bool:
        path = f"/users/{user_id}"
        resp = await self._connection.delete(
            path,
            error_msg=f"Could not create user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="Delete user"),
        )
        return resp.status_code == 204

    async def _rotate_key(self, user_id: str) -> str:
        path = f"/users/{user_id}/rotate-key"
        resp = await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not create user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="rotate key"),
        )
        resp_typed = _decode_json_response_dict(resp, "rotate key")
        assert resp_typed is not None
        return str(resp_typed["apikey"])

    async def _deactivate(self, user_id: str) -> None:
        path = f"/users/{user_id}/deactivate"
        await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not deactivate user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="deactivate key"),
        )

    async def _activate(self, user_id: str) -> None:
        path = f"/users/{user_id}/activate"
        await self._connection.post(
            path,
            weaviate_object={},
            error_msg=f"Could not activate user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="activate key"),
        )

    async def _get_user(self, user_id: str) -> WeaviateDBUser:
        path = f"/users/{user_id}"
        resp = await self._connection.get(
            path,
            error_msg=f"Could not activate user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get user"),
        )
        parsed = _decode_json_response_dict(resp, "get user")
        assert parsed is not None
        return cast(WeaviateDBUser, parsed)


class _UserDBAsync(_UsersBase):
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return {
            role["name"]: Role._from_weaviate_role(role)
            for role in await self._get_roles_of_user(user_id, USER_TYPE_DB)
        }

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

    async def activate(self, *, user_id: str) -> None:
        """Activate a deactivated user.

        Args:
            user_id: The id of the user.
        """
        return await self._activate(user_id)

    async def deactivate(self, *, user_id: str) -> None:
        """Deactivate an active user.

        Args:
            user_id: The id of the user.
        """
        return await self._deactivate(user_id)

    async def get(self, *, user_id: str) -> UserDB:
        """Get all information about an user.

        Args:
            user_id: The id of the user.
        """
        user = await self._get_user(user_id=user_id)

        return UserDB(
            user_id=user["userId"],
            roles=(
                {role["name"]: Role._from_weaviate_role(role) for role in user["roles"]}
                if user["roles"] is not None
                else {}
            ),
            active=user["active"],
        )


class _UserOIDCAsync(_UsersBase):
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return {
            role["name"]: Role._from_weaviate_role(role)
            for role in await self._get_roles_of_user(user_id, USER_TYPE_OIDC)
        }

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
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
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

    async def get_my_user(self) -> User:
        """Get the currently authenticated user.

        Returns:
            A user object.
        """
        user = await self._get_current_user()
        return User(
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
        ret_oidc = await self._oidc.get_assigned_roles(user_id)
        ret_db = await self._db.get_assigned_roles(user_id)
        return {**ret_oidc, **ret_db}

    # @deprecated(
    #     """This method is deprecated and will be removed in Q4 25.
    #             Please use `users.db.assign_roles` and/or `users.oidc.assign_roles` instead."""
    # )
    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await self.oidc.assign_roles(user_id=user_id, role_names=role_names)
        await self.db.assign_roles(user_id=user_id, role_names=role_names)

    # @deprecated(
    #     """This method is deprecated and will be removed in Q4 25.
    #             Please use `users.db.revoke_roles` and/or `users.oidc.revoke_roles` instead."""
    # )
    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await self.oidc.revoke_roles(user_id=user_id, role_names=role_names)
        await self.db.revoke_roles(user_id=user_id, role_names=role_names)

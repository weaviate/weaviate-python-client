from typing import Dict, List, Union, cast

from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.rbac.models import (
    Role,
    User,
    WeaviateRole,
    WeaviateUser,
)

from weaviate.util import _decode_json_response_dict


class _UsersBase:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection

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

    async def _get_roles_of_user(self, name: str) -> List[WeaviateRole]:
        path = f"/authz/users/{name}/roles"

        res = await self._connection.get(
            path,
            error_msg=f"Could not get roles of user {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )
        return cast(List[WeaviateRole], res.json())

    async def _assign_roles_to_user(self, roles: List[str], user: str) -> None:
        path = f"/authz/users/{user}/assign"

        await self._connection.post(
            path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not assign roles {roles} to user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    async def _revoke_roles_from_user(self, roles: List[str], user: str) -> None:
        path = f"/authz/users/{user}/revoke"

        await self._connection.post(
            path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )


class _UsersAsync(_UsersBase):

    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return {
            role["name"]: Role._from_weaviate_role(role)
            for role in await self._get_roles_of_user(user_id)
        }

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

    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names, user_id
        )

    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names, user_id
        )

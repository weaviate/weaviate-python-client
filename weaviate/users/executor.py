from typing import Any, Dict, Generic, List, Literal, Optional, Union, cast, overload
from typing_extensions import deprecated

from httpx import Response

from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionType
from weaviate.rbac.models import (
    Role,
    RoleBase,
    WeaviateDBUserRoleNames,
    UserTypes,
)
from weaviate.users.users import (
    USER_TYPE_DB,
    USER_TYPE_OIDC,
    USER_TYPE,
    UserDB,
    OwnUser,
)
from weaviate.util import _decode_json_response_dict


class _BaseExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def _get_roles_of_user(
        self,
        user_id: str,
        user_type: USER_TYPE,
        include_permissions: bool,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        path = f"/authz/users/{user_id}/roles/{user_type}"

        def resp(res: Response) -> Union[Dict[str, Role], Dict[str, RoleBase]]:
            roles = res.json()
            if include_permissions:
                return {role["name"]: Role._from_weaviate_role(role) for role in roles}
            return {role["name"]: RoleBase(role["name"]) for role in roles}

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            params={"includeFullRoles": include_permissions},
            error_msg=f"Could not get roles of user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    def _get_roles_of_user_deprecated(
        self,
        user_id: str,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        path = f"/authz/users/{user_id}/roles"

        def resp(res: Response) -> Union[Dict[str, Role], Dict[str, RoleBase]]:
            return {role["name"]: Role._from_weaviate_role(role) for role in res.json()}

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get roles of user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    def _assign_roles_to_user(
        self,
        roles: List[str],
        user_id: str,
        user_type: Optional[USER_TYPE],
    ) -> executor.Result[None]:
        path = f"/authz/users/{user_id}/assign"

        payload: Dict[str, Any] = {"roles": roles}
        if user_type is not None:
            payload["userType"] = user_type

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
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
    ) -> executor.Result[None]:
        path = f"/authz/users/{user_id}/revoke"

        payload: Dict[str, Any] = {"roles": roles}
        if user_type is not None:
            payload["userType"] = user_type

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )


class _UsersExecutor(Generic[ConnectionType], _BaseExecutor[ConnectionType]):
    def get_my_user(self) -> executor.Result[OwnUser]:
        """Get the currently authenticated user.

        Returns:
            A user object.
        """
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

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.get_assigned_roles` and/or `users.oidc.get_assigned_roles` instead."""
    )
    def get_assigned_roles(self, user_id: str) -> executor.Result[Dict[str, Role]]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        # cast here because the deprecated method is only used in the deprecated class and this type is known
        return cast(Dict[str, Role], self._get_roles_of_user_deprecated(user_id))

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.assign_roles` and/or `users.oidc.assign_roles` instead."""
    )
    def assign_roles(
        self,
        *,
        user_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        return self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            None,
        )

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.revoke_roles` and/or `users.oidc.revoke_roles` instead."""
    )
    def revoke_roles(
        self,
        *,
        user_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        return self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            None,
        )


class _UsersOIDCExecutor(Generic[ConnectionType], _BaseExecutor[ConnectionType]):
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = False
    ) -> executor.Result[Dict[str, RoleBase]]: ...

    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True]
    ) -> executor.Result[Dict[str, Role]]: ...

    @overload
    def get_assigned_roles(
        self,
        *,
        user_id: str,
        include_permissions: bool = False,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]: ...

    def get_assigned_roles(
        self,
        *,
        user_id: str,
        include_permissions: bool = False,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        """Get the roles assigned to a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return self._get_roles_of_user(
            user_id,
            USER_TYPE_OIDC,
            include_permissions,
        )

    def assign_roles(
        self,
        *,
        user_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Assign roles to a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        return self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_OIDC,
        )

    def revoke_roles(
        self,
        *,
        user_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Revoke roles from a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        return self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_OIDC,
        )


class _UsersDBExecutor(Generic[ConnectionType], _BaseExecutor[ConnectionType]):
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = False
    ) -> executor.Result[Dict[str, RoleBase]]: ...

    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True]
    ) -> executor.Result[Dict[str, Role]]: ...

    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]: ...

    def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return self._get_roles_of_user(
            user_id,
            USER_TYPE_DB,
            include_permissions,
        )

    def assign_roles(
        self,
        *,
        user_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        return self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_DB,
        )

    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> executor.Result[None]:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        return self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names,
            user_id,
            USER_TYPE_DB,
        )

    def create(self, *, user_id: str) -> executor.Result[str]:
        """Create a new db user.

        Args:
            user_id: The id of the new user.
        """

        def resp(res: Response) -> str:
            resp = _decode_json_response_dict(res, "Create user")
            assert resp is not None
            return str(resp["apikey"])

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/users/db/{user_id}",
            weaviate_object={},
            error_msg=f"Could not create user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create user"),
        )

    def delete(self, *, user_id: str) -> executor.Result[bool]:
        """Delete a (dynamic) db user.

        Args:
            user_id: The id of the user to be deleted.
        """

        def resp(res: Response) -> bool:
            return res.status_code == 204

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=f"/users/db/{user_id}",
            error_msg=f"Could not delete user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[204, 404], error="Delete user"),
        )

    def rotate_key(self, *, user_id: str) -> executor.Result[str]:
        """Rotate the key of a new db user.

        Args:
            user_id: The id of the user.
        """

        def resp(res: Response) -> str:
            resp = _decode_json_response_dict(res, "Rotate key")
            assert resp is not None
            return str(resp["apikey"])

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/users/db/{user_id}/rotate-key",
            weaviate_object={},
            error_msg=f"Could not rotate key for user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Rotate key"),
        )

    def activate(self, *, user_id: str) -> executor.Result[bool]:
        """Activate a deactivated user.

        Args:
            user_id: The id of the user.
        """

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/users/db/{user_id}/activate",
            weaviate_object={},
            error_msg=f"Could not activate user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 409], error="Activate user"),
        )

    def deactivate(self, *, user_id: str, revoke_key: bool = False) -> executor.Result[bool]:
        """Deactivate an active user.

        Args:
            user_id: The id of the user.
            revoke_key: If True, the old key will be revoked and needs to be rotated.
        """

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=f"/users/db/{user_id}/deactivate",
            weaviate_object={"revoke_key": revoke_key},
            error_msg=f"Could not deactivate user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 409], error="Deactivate user"),
        )

    def get(self, *, user_id: str) -> executor.Result[Optional[UserDB]]:
        """Get all information about an user.

        Args:
            user_id: The id of the user.
        """

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

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=f"/users/db/{user_id}",
            error_msg=f"Could not get user '{user_id}'",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="get user"),
        )

    def list_all(self) -> executor.Result[List[UserDB]]:
        """List all DB users."""

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

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path="/users/db",
            error_msg="Could not list all users",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="list all users"),
        )

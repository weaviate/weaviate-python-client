from typing import Awaitable, Dict, Generic, List, Union, cast, overload

from httpx import Response

from weaviate.connect.executor import ExecutorResult, execute, raise_exception
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync, ConnectionSync, ConnectionType
from weaviate.rbac.models import (
    Role,
    User,
    WeaviateRole,
    WeaviateUser,
)

from weaviate.util import _decode_json_response_dict


class _UsersExecutor:
    @overload
    def get_current_user(self, *, connection: ConnectionAsync) -> Awaitable[User]:
        ...

    @overload
    def get_current_user(self, *, connection: ConnectionSync) -> User:
        ...
        
    def get_current_user(self, *, connection: Connection) -> ExecutorResult[User]:
        path = "/users/own-info"

        def resp(res: Response) -> User:
            parsed = _decode_json_response_dict(res, "Get current user")
            assert parsed is not None
            # The API returns "username" for 1.29 instead of "user_id"
            user_id = parsed["username"] if "username" in parsed else parsed["user_id"]
            return User(
                user_id=user_id,
                roles=(
                    {role["name"]: Role._from_weaviate_role(role) for role in parsed["roles"]}
                    if parsed["roles"] is not None
                    else {}
                )
            )

        def exc(e: Exception) -> User:
            raise e

        return execute(
            response_callback=resp,
            exception_callback=exc,
            method=connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    @overload
    def get_roles_of_user(self, *, connection: ConnectionAsync, name: str) -> Awaitable[Dict[str, Role]]:
        ...

    @overload
    def get_roles_of_user(self, *, connection: ConnectionSync, name: str) -> Dict[str, Role]:
        ...

    def get_roles_of_user(self, *, connection: Connection, name: str) -> ExecutorResult[Dict[str, Role]]:
        path = f"/authz/users/{name}/roles"

        def resp(res: Response) -> Dict[str, Role]:
            return {
                role["name"]: Role._from_weaviate_role(role)
                for role in res.json()
            }

        def exc(e: Exception) -> Dict[str, Role]:
            raise e
        
        return execute(
            response_callback=resp,
            exception_callback=exc,
            method=connection.get,
            path=path,
            error_msg=f"Could not get roles of user {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    @overload
    def assign_roles_to_user(self, *, connection: ConnectionAsync, roles: List[str], user: str) -> Awaitable[None]:
        ...

    @overload
    def assign_roles_to_user(self, *, connection: ConnectionSync, roles: List[str], user: str) -> None:
        ...

    def assign_roles_to_user(self, *, connection: Connection, roles: List[str], user: str) -> ExecutorResult[None]:
        path = f"/authz/users/{user}/assign"

        return execute(
            response_callback=lambda res: None,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not assign roles {roles} to user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    @overload
    def revoke_roles_from_user(self, *, connection: ConnectionAsync, roles: List[str], user: str) -> Awaitable[None]:
        ...

    @overload
    def revoke_roles_from_user(self, *, connection: ConnectionSync, roles: List[str], user: str) -> None:
        ...

    def revoke_roles_from_user(self, *, connection: Connection, roles: List[str], user: str) -> ExecutorResult[None]:
        path = f"/authz/users/{user}/revoke"

        return execute(
            response_callback=lambda res: None,
            exception_callback=raise_exception,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )


class _UsersBase(Generic[ConnectionType]):
    _executor = _UsersExecutor()
        
    def __init__(self, connection: ConnectionType) -> None:
        self._connection = connection


class _UsersAsync(_UsersBase[ConnectionAsync]):
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return await self._executor.get_roles_of_user(connection=self._connection, name=user_id)

    async def get_my_user(self) -> User:
        """Get the currently authenticated user.

        Returns:
            A user object.
        """
        return await self._executor.get_current_user(connection=self._connection)

    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await self._executor.assign_roles_to_user(
            connection=self._connection,
            roles=[role_names] if isinstance(role_names, str) else role_names,
            user=user_id
        )

    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await self._executor.revoke_roles_from_user(
            connection=self._connection,
            roles=[role_names] if isinstance(role_names, str) else role_names,
            user=user_id
        )

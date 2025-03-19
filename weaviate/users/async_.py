from typing import Dict, Generic, List, Union

from weaviate.connect.v4 import ConnectionAsync, ConnectionType
from weaviate.rbac.models import (
    Role,
    User,
)
from weaviate.users.executor import _UsersExecutor


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
            user=user_id,
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
            user=user_id,
        )

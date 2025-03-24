from typing import Dict, Generic, List, Optional, Union
from typing_extensions import deprecated

from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionType
from weaviate.rbac.models import (
    Role,
)
from weaviate.users.executor import _DeprecatedExecutor, _DBExecutor, _OIDCExecutor, OwnUser, UserDB


class _UsersOIDCBase(Generic[ConnectionType]):
    _executor = _OIDCExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection


class _UsersOIDCAsync(_UsersOIDCBase[ConnectionAsync]):
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return await aresult(
            self._executor.get_assigned_roles(user_id, connection=self._connection)
        )

    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await aresult(
            self._executor.assign_roles(
                role_names=role_names, user_id=user_id, connection=self._connection
            )
        )

    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await aresult(
            self._executor.revoke_roles(
                role_names=role_names, user_id=user_id, connection=self._connection
            )
        )


class _UsersDBBase(Generic[ConnectionType]):
    _executor = _DBExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection


class _UsersDBAsync(_UsersDBBase[ConnectionAsync]):
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return await aresult(
            self._executor.get_assigned_roles(user_id, connection=self._connection)
        )

    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        await aresult(
            self._executor.assign_roles(
                connection=self._connection,
                role_names=role_names,
                user_id=user_id,
            )
        )

    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        await aresult(
            self._executor.revoke_roles(
                connection=self._connection,
                role_names=role_names,
                user_id=user_id,
            )
        )

    async def create(self, *, user_id: str) -> str:
        """Create a new db user.

        Args:
            user_id: The id of the new user.
        """
        return await aresult(self._executor.create(user_id=user_id, connection=self._connection))

    async def delete(self, *, user_id: str) -> bool:
        """Delete a (dynamic) db user.

        Args:
            user_id: The id of the user to be deleted.
        """
        return await self._executor.delete(user_id=user_id, connection=self._connection)

    async def rotate_key(self, *, user_id: str) -> str:
        """Rotate the key of a new db user.

        Args:
            user_id: The id of the user.
        """
        return await self._executor.rotate_key(user_id=user_id, connection=self._connection)

    async def activate(self, *, user_id: str) -> bool:
        """Activate a deactivated user.

        Args:
            user_id: The id of the user.
        """
        return await self._executor.activate(user_id=user_id, connection=self._connection)

    async def deactivate(self, *, user_id: str) -> bool:
        """Deactivate an active user.

        Args:
            user_id: The id of the user.
        """
        return await self._executor.deactivate(user_id=user_id, connection=self._connection)

    async def get(self, *, user_id: str) -> Optional[UserDB]:
        """Get all information about an user.

        Args:
            user_id: The id of the user.
        """
        return await aresult(self._executor.get(user_id=user_id, connection=self._connection))

    async def list_all(self) -> List[UserDB]:
        """List all DB users."""
        return await aresult(self._executor.list_all(connection=self._connection))


class _UsersBase(Generic[ConnectionType]):
    _executor = _DeprecatedExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection


class _UsersAsync(_UsersBase[ConnectionAsync]):
    def __init__(self, connection: ConnectionAsync) -> None:
        super().__init__(connection)
        self.db = _UsersDBAsync(connection)
        self.oidc = _UsersOIDCAsync(connection)

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.get_assigned_roles` and/or `users.oidc.get_assigned_roles` instead."""
    )
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return await aresult(
            self._executor.get_assigned_roles(user_id, connection=self._connection)
        )

    async def get_my_user(self) -> OwnUser:
        """Get the currently authenticated user.

        Returns:
            A user object.
        """
        return await aresult(self._executor.get_my_user(connection=self._connection))

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
        await aresult(
            self._executor.assign_roles(
                connection=self._connection,
                role_names=role_names,
                user_id=user_id,
            )
        )

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
        await aresult(
            self._executor.revoke_roles(
                connection=self._connection,
                role_names=role_names,
                user_id=user_id,
            )
        )

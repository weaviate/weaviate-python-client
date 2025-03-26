from abc import abstractmethod
from typing import Dict, Generic, List, Optional, Union

from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.rbac.models import Role, RoleBase
from weaviate.users.executor import _DeprecatedExecutor, _DBExecutor, _OIDCExecutor, OwnUser, UserDB


class _UsersOIDCBase(Generic[ConnectionType]):
    _executor = _OIDCExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection

    @abstractmethod
    def get_assigned_roles(
        self, user_id: str, include_permissions: bool = False
    ) -> ExecutorResult[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        """Get the roles assigned to a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        raise NotImplementedError()

    @abstractmethod
    def assign_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> ExecutorResult[None]:
        """Assign roles to a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        raise NotImplementedError()

    @abstractmethod
    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> ExecutorResult[None]:
        """Revoke roles from a user specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        raise NotImplementedError()


class _UsersDBBase(Generic[ConnectionType]):
    _executor = _DBExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection

    @abstractmethod
    def get_assigned_roles(
        self, user_id: str, include_permissions: bool = False
    ) -> ExecutorResult[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        raise NotImplementedError()

    @abstractmethod
    def assign_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> ExecutorResult[None]:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        raise NotImplementedError()

    @abstractmethod
    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> ExecutorResult[None]:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        raise NotImplementedError()

    @abstractmethod
    def create(self, *, user_id: str) -> ExecutorResult[str]:
        """Create a new db user.

        Args:
            user_id: The id of the new user.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, *, user_id: str) -> ExecutorResult[bool]:
        """Delete a (dynamic) db user.

        Args:
            user_id: The id of the user to be deleted.
        """
        raise NotImplementedError()

    @abstractmethod
    def rotate_key(self, *, user_id: str) -> ExecutorResult[str]:
        """Rotate the key of a new db user.

        Args:
            user_id: The id of the user.
        """
        raise NotImplementedError()

    @abstractmethod
    def activate(self, *, user_id: str) -> ExecutorResult[bool]:
        """Activate a deactivated user.

        Args:
            user_id: The id of the user.
        """
        raise NotImplementedError()

    @abstractmethod
    def deactivate(self, *, user_id: str) -> ExecutorResult[bool]:
        """Deactivate an active user.

        Args:
            user_id: The id of the user.
        """
        raise NotImplementedError()

    @abstractmethod
    def get(self, *, user_id: str) -> ExecutorResult[Optional[UserDB]]:
        """Get all information about an user.

        Args:
            user_id: The id of the user.
        """
        raise NotImplementedError()

    @abstractmethod
    def list_all(self) -> ExecutorResult[List[UserDB]]:
        """List all DB users."""
        raise NotImplementedError()


class _UsersBase(Generic[ConnectionType]):
    _executor = _DeprecatedExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection

    @abstractmethod
    def get_assigned_roles(self, user_id: str) -> ExecutorResult[Dict[str, Role]]:
        """Get the roles assigned to a user.

        Args:
            user_id: The user ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_my_user(self) -> ExecutorResult[OwnUser]:
        """Get the currently authenticated user.

        Returns:
            A user object.
        """
        raise NotImplementedError()

    @abstractmethod
    def assign_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> ExecutorResult[None]:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user_id: The user to assign the roles to.
        """
        raise NotImplementedError()

    @abstractmethod
    def revoke_roles(
        self, *, user_id: str, role_names: Union[str, List[str]]
    ) -> ExecutorResult[None]:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user_id: The user to revoke the roles from.
        """
        raise NotImplementedError()

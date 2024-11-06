from weaviate.connect import ConnectionV4
from weaviate.rbac.models import Permissions


class _Permissions:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection

    def add(self, *, permissions: Permissions, role: str) -> None:
        """Add permissions to a role.

        Args:
            permissions: The permissions to add to the role.
            role: The role to add the permissions to.
        """
        ...

    def remove(self, *, permissions: Permissions, role: str) -> None:
        """Remove permissions from a role.

        Args:
            actions: The actions to remove from the role.
            role: The role to remove the permissions from.
        """
        ...

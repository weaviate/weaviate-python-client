from typing import Dict, Generic, List, Literal, Union, overload

from httpx import Response

from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType, _ExpectedStatusCodes
from weaviate.rbac.models import (
    Role,
    RoleBase,
)
from weaviate.users.users import (
    USER_TYPE,
    USER_TYPE_OIDC,
)
from weaviate.util import escape_string


class _BaseExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def _get_roles_of_group(
        self,
        group_id: str,
        group_type: USER_TYPE,
        include_permissions: bool,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        path = f"/authz/groups/{escape_string(group_id)}/roles/{group_type}"

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
            error_msg=f"Could not get roles of group {group_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of group"),
        )

    def _assign_roles_to_group(
        self,
        roles: List[str],
        group_id: str,
        group_type: USER_TYPE,
    ) -> executor.Result[None]:
        path = f"/authz/groups/{escape_string(group_id)}/assign"

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object={"roles": roles, "groupType": group_type},
            error_msg=f"Could not assign roles {roles} to group {group_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign group to roles"),
        )

    def _revoke_roles_from_group(
        self,
        roles: Union[str, List[str]],
        group_id: str,
        group_type: USER_TYPE,
    ) -> executor.Result[None]:
        path = f"/authz/groups/{escape_string(group_id)}/revoke"

        def resp(res: Response) -> None:
            pass

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object={"roles": roles, "groupType": group_type},
            error_msg=f"Could not revoke roles {roles} from group {group_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke group from user"),
        )

    def _get_known_group_names(self, group_type: USER_TYPE) -> executor.Result[List[str]]:
        path = f"/authz/groups/{group_type}"

        def resp(res: Response) -> List[str]:
            groups = res.json()
            assert isinstance(groups, list), "Expected a list of group names"
            return groups

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get known groups for group type {group_type}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get known groups"),
        )


class _GroupsOIDCExecutor(Generic[ConnectionType], _BaseExecutor[ConnectionType]):
    @overload
    def get_assigned_roles(
        self, *, group_id: str, include_permissions: Literal[False] = False
    ) -> executor.Result[Dict[str, RoleBase]]: ...

    @overload
    def get_assigned_roles(
        self, *, group_id: str, include_permissions: Literal[True]
    ) -> executor.Result[Dict[str, Role]]: ...

    @overload
    def get_assigned_roles(
        self,
        *,
        group_id: str,
        include_permissions: bool = False,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]: ...

    def get_assigned_roles(
        self,
        *,
        group_id: str,
        include_permissions: bool = False,
    ) -> executor.Result[Union[Dict[str, Role], Dict[str, RoleBase]]]:
        """Get the roles assigned to a group specific to the configured OIDC's dynamic auth functionality.

        Args:
            group_id: The group ID to get the roles for.

        Returns:
            A dictionary with role names as keys and the `Role` objects as values.
        """
        return self._get_roles_of_group(
            group_id,
            USER_TYPE_OIDC,
            include_permissions,
        )

    def assign_roles(
        self,
        *,
        group_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Assign roles to a group specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to assign to the group.
            group_id: The group to assign the roles to.
        """
        return self._assign_roles_to_group(
            [role_names] if isinstance(role_names, str) else role_names,
            group_id,
            USER_TYPE_OIDC,
        )

    def revoke_roles(
        self,
        *,
        group_id: str,
        role_names: Union[str, List[str]],
    ) -> executor.Result[None]:
        """Revoke roles from a group specific to the configured OIDC's dynamic auth functionality.

        Args:
            role_names: The names of the roles to revoke from the group.
            group_id: The group to revoke the roles from.
        """
        return self._revoke_roles_from_group(
            [role_names] if isinstance(role_names, str) else role_names,
            group_id,
            USER_TYPE_OIDC,
        )

    def get_known_group_names(self) -> executor.Result[List[str]]:
        """Get the known group names specific to the configured OIDC's dynamic auth functionality.

        Returns:
            A list of known group names.
        """
        return self._get_known_group_names(
            USER_TYPE_OIDC,
        )

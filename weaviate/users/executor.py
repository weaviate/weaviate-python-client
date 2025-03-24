from typing import Dict, List, Union

from httpx import Response

from weaviate.connect.executor import ExecutorResult, execute
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection
from weaviate.rbac.models import (
    Role,
    User,
)

from weaviate.util import _decode_json_response_dict


class _UsersExecutor:
    def get_my_user(self, connection: Connection) -> ExecutorResult[User]:
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
                ),
            )

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    def get_assigned_roles(
        self,
        user_id: str,
        *,
        connection: Connection,
    ) -> ExecutorResult[Dict[str, Role]]:
        path = f"/authz/users/{user_id}/roles"

        def resp(res: Response) -> Dict[str, Role]:
            return {role["name"]: Role._from_weaviate_role(role) for role in res.json()}

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg=f"Could not get roles of user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    def assign_roles(
        self, *, role_names: Union[str, List[str]], user_id: str, connection: Connection
    ) -> ExecutorResult[None]:
        path = f"/authz/users/{user_id}/assign"
        roles = role_names if isinstance(role_names, list) else [role_names]

        def resp(res: Response) -> None:
            pass

        return execute(
            response_callback=resp,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not assign roles {roles} to user {user_id}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    def revoke_roles(
        self, connection: Connection, *, role_names: Union[str, List[str]], user: str
    ) -> ExecutorResult[None]:
        path = f"/authz/users/{user}/revoke"
        roles = role_names if isinstance(role_names, list) else [role_names]

        def resp(res: Response) -> None:
            pass

        return execute(
            response_callback=resp,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )

from typing import Awaitable, Dict, List, overload

from httpx import Response

from weaviate.connect.executor import ExecutorResult, execute, raise_exception
from weaviate.connect.v4 import _ExpectedStatusCodes, Connection, ConnectionAsync, ConnectionSync
from weaviate.rbac.models import (
    Role,
    User,
)

from weaviate.util import _decode_json_response_dict


class _UsersExecutor:
    def get_current_user(self, *, connection: ConnectionAsync) -> Awaitable[User]:
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

    def get_roles_of_user(
        self, *, connection: ConnectionAsync, name: str
    ) -> Awaitable[Dict[str, Role]]:
        path = f"/authz/users/{name}/roles"

        def resp(res: Response) -> Dict[str, Role]:
            return {role["name"]: Role._from_weaviate_role(role) for role in res.json()}

        return execute(
            response_callback=resp,
            method=connection.get,
            path=path,
            error_msg=f"Could not get roles of user {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )

    def assign_roles_to_user(
        self, *, connection: ConnectionAsync, roles: List[str], user: str
    ) -> Awaitable[None]:
        path = f"/authz/users/{user}/assign"

        return execute(
            response_callback=lambda res: None,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not assign roles {roles} to user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    def revoke_roles_from_user(
        self, *, connection: ConnectionAsync, roles: List[str], user: str
    ) -> Awaitable[None]:
        path = f"/authz/users/{user}/revoke"

        return execute(
            response_callback=lambda res: None,
            method=connection.post,
            path=path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )

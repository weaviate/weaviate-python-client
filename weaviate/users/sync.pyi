from typing import Dict, List, Union
from weaviate.users.users import _UsersBase

from weaviate.rbac.models import Role, User

class _Users(_UsersBase):
    def get_my_user(self) -> User: ...
    def get_roles(self, user_id: str) -> Dict[str, Role]: ...
    def assign_roles(self, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    def revoke_roles(self, user_id: str, role_names: Union[str, List[str]]) -> None: ...

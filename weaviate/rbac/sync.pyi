from typing import List, Optional, Union
from weaviate.rbac.roles import _RolesBase
from weaviate.rbac.models import Permissions, Role, User

class _Roles(_RolesBase):
    def list_all(self) -> List[Role]: ...
    def by_name(self, role: str) -> Optional[Role]: ...
    def by_user(self, user: str) -> List[Role]: ...
    def users(self, role: str) -> List[User]: ...
    def delete(self, role: str) -> None: ...
    def create(self, *, name: str, permissions: Permissions) -> Role: ...
    def assign(self, *, roles: Union[str, List[str]], user: str) -> None: ...
    def revoke(self, *, roles: Union[str, List[str]], user: str) -> None: ...
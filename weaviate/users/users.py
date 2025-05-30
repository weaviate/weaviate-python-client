from dataclasses import dataclass
from typing import Dict, Final, List, Literal

from weaviate.rbac.models import (
    Role,
    UserTypes,
)

USER_TYPE_DB: Final = "db"
USER_TYPE_OIDC: Final = "oidc"
USER_TYPE = Literal["db", "oidc"]


@dataclass
class OwnUser:
    user_id: str
    roles: Dict[str, Role]


@dataclass
class UserBase:
    user_id: str
    role_names: List[str]
    user_type: UserTypes


@dataclass
class UserDB(UserBase):
    user_type: UserTypes
    active: bool


@dataclass
class UserOIDC(UserBase):
    user_type: UserTypes = UserTypes.OIDC

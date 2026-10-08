from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Final, List, Literal, Optional

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
    groups: List[str]


@dataclass
class UserBase:
    user_id: str
    role_names: List[str]
    user_type: UserTypes


@dataclass
class UserDB(UserBase):
    user_type: UserTypes
    active: bool
    created_at: Optional[datetime] = field(default=None)
    last_used_time: Optional[datetime] = field(default=None)
    api_key_first_letters: Optional[str] = field(default=None)


@dataclass
class UserOIDC(UserBase):
    user_type: UserTypes = UserTypes.OIDC

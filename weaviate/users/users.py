from dataclasses import dataclass
import datetime
from typing import Dict, Final, Generic, List, Literal, TypeVar

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


# generic type for UserDB
T = TypeVar("T")


@dataclass
class UserDB(UserBase, Generic[T]):
    user_type: UserTypes
    active: bool
    created_at: datetime.datetime
    last_used: T
    apikey_first_letters: str


@dataclass
class UserOIDC(UserBase):
    user_type: UserTypes = UserTypes.OIDC

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytest

from weaviate.rbac.models import UserTypes
from weaviate.users.base import _UsersDBExecutor

# Go's zero time, as the server serializes it when a timestamp is not set
GO_ZERO_TIME = "0001-01-01T00:00:00.000Z"
REAL_CREATED_AT = "2026-11-08T09:39:44.687000Z"
REAL_CREATED_AT_DT = datetime(2026, 11, 8, 9, 39, 44, 687000, tzinfo=timezone.utc)


def _db_user(
    user_id: str,
    *,
    created_at: Optional[str],
    last_used_at: Optional[str] = None,
    user_type: str = "db_env_user",
) -> Dict[str, Any]:
    return {
        "active": True,
        "createdAt": created_at,
        "dbUserType": user_type,
        "lastUsedAt": last_used_at,
        "roles": ["root"],
        "userId": user_id,
    }


class _FakeConnection:
    """Stand-in for a connection: answers GETs with a canned JSON payload."""

    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code
        self.requests: List[Tuple[str, Optional[Dict[str, Any]]]] = []

    def get(
        self, path: str, params: Optional[Dict[str, Any]] = None, **kwargs: Any
    ) -> httpx.Response:
        self.requests.append((path, params))
        return httpx.Response(self._status_code, json=self._payload)


def test_get_env_user_with_zero_created_at_returns_none() -> None:
    # Regression test for #2243: the server sends Go's zero time for the
    # createdAt of an env-defined user, which must read as None, exactly like
    # lastUsedAt already does.
    conn = _FakeConnection(_db_user("admin", created_at=GO_ZERO_TIME, last_used_at=GO_ZERO_TIME))
    executor = _UsersDBExecutor(conn)  # type: ignore[arg-type]

    user = executor.get(user_id="admin", include_last_used_time=True)

    assert user is not None
    assert user.user_id == "admin"
    assert user.user_type == UserTypes.DB_STATIC
    assert user.created_at is None
    assert user.last_used_time is None
    assert conn.requests == [("/users/db/admin", {"includeLastUsedTime": True})]


def test_get_user_with_real_created_at_parses() -> None:
    conn = _FakeConnection(
        _db_user("alice", created_at=REAL_CREATED_AT, last_used_at=None, user_type="db_user")
    )
    executor = _UsersDBExecutor(conn)  # type: ignore[arg-type]

    user = executor.get(user_id="alice", include_last_used_time=True)

    assert user is not None
    assert user.user_id == "alice"
    assert user.user_type == UserTypes.DB_DYNAMIC
    assert user.created_at == REAL_CREATED_AT_DT
    assert user.last_used_time is None


def test_list_all_env_user_with_zero_created_at_returns_none() -> None:
    conn = _FakeConnection(
        [
            _db_user("admin", created_at=GO_ZERO_TIME, last_used_at=GO_ZERO_TIME),
            _db_user(
                "alice",
                created_at=REAL_CREATED_AT,
                last_used_at=None,
                user_type="db_user",
            ),
        ]
    )
    executor = _UsersDBExecutor(conn)  # type: ignore[arg-type]

    users = executor.list_all(include_last_used_time=True)

    assert len(users) == 2
    assert users[0].user_id == "admin"
    assert users[0].created_at is None
    assert users[0].last_used_time is None
    assert users[1].user_id == "alice"
    assert users[1].created_at == REAL_CREATED_AT_DT
    assert users[1].last_used_time is None
    assert conn.requests == [("/users/db", {"includeLastUsedTime": True})]


@pytest.mark.parametrize(
    "value,expected",
    [
        pytest.param(None, None, id="none"),
        pytest.param(GO_ZERO_TIME, None, id="go-zero-time"),
        pytest.param(REAL_CREATED_AT, REAL_CREATED_AT_DT, id="real-timestamp"),
    ],
)
def test_parse_optional_timestamp(value: Optional[str], expected: Optional[datetime]) -> None:
    from weaviate.users.base import _parse_optional_timestamp

    assert _parse_optional_timestamp(value) == expected

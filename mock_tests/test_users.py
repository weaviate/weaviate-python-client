import json
from datetime import datetime, timezone
import grpc
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC

USER_DATA = {
    "active": True,
    "apiKeyFirstLetters": "UzJ",
    "createdAt": "2026-02-24T19:15:18.574Z",
    "dbUserType": "db_user",
    "lastUsedAt": "2026-02-25T20:57:36.419Z",
    "roles": ["R1", "admin"],
    "userId": "test-user",
}

USER_DATA_NO_LAST_USED = {k: v for k, v in USER_DATA.items() if k != "lastUsedAt"}

USERS_DATA = [
    USER_DATA,
    {**USER_DATA, "userId": "test-user-2"},
]

USERS_DATA_NO_LAST_USED = [
    USER_DATA_NO_LAST_USED,
    {**USER_DATA_NO_LAST_USED, "userId": "test-user-2"},
]

EXPECTED_CREATED_AT = datetime(2026, 2, 24, 19, 15, 18, 574000, tzinfo=timezone.utc)
EXPECTED_LAST_USED_AT = datetime(2026, 2, 25, 20, 57, 36, 419000, tzinfo=timezone.utc)


def test_get_user_without_last_used_time(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    captured: dict = {}

    def handler(request: Request) -> Response:
        captured["params"] = dict(request.args)
        return Response(json.dumps(USER_DATA_NO_LAST_USED), content_type="application/json", status=200)

    weaviate_no_auth_mock.expect_request("/v1/users/db/test-user").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        user = client.users.db.get(user_id="test-user")

    assert user is not None
    assert user.user_id == "test-user"
    assert user.active is True
    assert user.created_at == EXPECTED_CREATED_AT
    assert user.last_used_time is None
    assert user.api_key_first_letters == "UzJ"
    assert captured["params"].get("includeLastUsedTime") in ("False", "false")


def test_get_user_with_last_used_time(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    captured: dict = {}

    def handler(request: Request) -> Response:
        captured["params"] = dict(request.args)
        return Response(json.dumps(USER_DATA), content_type="application/json", status=200)

    weaviate_no_auth_mock.expect_request("/v1/users/db/test-user").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        user = client.users.db.get(user_id="test-user", include_last_used_time=True)

    assert user is not None
    assert user.last_used_time == EXPECTED_LAST_USED_AT
    assert user.created_at == EXPECTED_CREATED_AT
    assert captured["params"].get("includeLastUsedTime") in ("True", "true")


def test_get_user_not_found(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    weaviate_no_auth_mock.expect_request("/v1/users/db/nonexistent").respond_with_response(
        Response("{}", content_type="application/json", status=404)
    )

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        user = client.users.db.get(user_id="nonexistent")

    assert user is None


def test_list_all_without_last_used_time(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    captured: dict = {}

    def handler(request: Request) -> Response:
        captured["params"] = dict(request.args)
        return Response(json.dumps(USERS_DATA_NO_LAST_USED), content_type="application/json", status=200)

    weaviate_no_auth_mock.expect_request("/v1/users/db").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        users = client.users.db.list_all()

    assert len(users) == 2
    assert users[0].user_id == "test-user"
    assert users[0].created_at == EXPECTED_CREATED_AT
    assert users[0].last_used_time is None
    assert users[0].api_key_first_letters == "UzJ"
    assert captured["params"].get("includeLastUsedTime") in ("False", "false")


def test_list_all_with_last_used_time(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    captured: dict = {}

    def handler(request: Request) -> Response:
        captured["params"] = dict(request.args)
        return Response(json.dumps(USERS_DATA), content_type="application/json", status=200)

    weaviate_no_auth_mock.expect_request("/v1/users/db").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        users = client.users.db.list_all(include_last_used_time=True)

    assert len(users) == 2
    for user in users:
        assert user.last_used_time == EXPECTED_LAST_USED_AT
        assert user.created_at == EXPECTED_CREATED_AT
    assert captured["params"].get("includeLastUsedTime") in ("True", "true")


def test_get_user_missing_created_at(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    data = {k: v for k, v in USER_DATA.items() if k != "createdAt"}
    weaviate_no_auth_mock.expect_request("/v1/users/db/test-user").respond_with_response(
        Response(json.dumps(data), content_type="application/json", status=200)
    )

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        user = client.users.db.get(user_id="test-user")

    assert user is not None
    assert user.created_at is None
    assert user.last_used_time == EXPECTED_LAST_USED_AT


def test_get_user_missing_api_key_first_letters(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    data = {k: v for k, v in USER_DATA.items() if k != "apiKeyFirstLetters"}
    weaviate_no_auth_mock.expect_request("/v1/users/db/test-user").respond_with_response(
        Response(json.dumps(data), content_type="application/json", status=200)
    )

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        user = client.users.db.get(user_id="test-user")

    assert user is not None
    assert user.api_key_first_letters is None
    assert user.created_at == EXPECTED_CREATED_AT


def test_get_user_last_used_time_parsed_when_include_false(
    weaviate_no_auth_mock: HTTPServer, start_grpc_server: grpc.Server
) -> None:
    """If the API returns lastUsedAt the client must parse it regardless of include_last_used_time."""
    captured: dict = {}

    def handler(request: Request) -> Response:
        captured["params"] = dict(request.args)
        return Response(json.dumps(USER_DATA), content_type="application/json", status=200)

    weaviate_no_auth_mock.expect_request("/v1/users/db/test-user").respond_with_handler(handler)

    with weaviate.connect_to_local(
        host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
    ) as client:
        user = client.users.db.get(user_id="test-user")  # include_last_used_time defaults to False

    assert user is not None
    assert user.last_used_time == EXPECTED_LAST_USED_AT
    assert captured["params"].get("includeLastUsedTime") in ("False", "false")

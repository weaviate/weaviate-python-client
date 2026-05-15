"""Mock tests for the namespaces module and namespace-aware DB user creation.

These tests exercise the HTTP contract (URLs, request bodies, status codes,
response shape) without requiring a running Weaviate cluster. They are the
counterpart to the integration tests in ``integration/test_namespaces.py``
and are responsible for catching:

- Regressions in the URL paths the client sends to the server.
- Regressions in the JSON body shape we send (e.g. dropping ``namespace`` from
  user-create payloads).
- Regressions in response parsing, including the boundary case where the
  server returns ``null`` for an empty namespace list.
- A future contributor accidentally lowering the version requirement guard
  on namespace endpoints (currently 1.38.0+).
"""

import json
from typing import Any, Callable, Dict, Generator, Tuple

import grpc
import pytest
from pytest_httpserver import HTTPServer
from werkzeug.wrappers import Request, Response

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.namespaces.models import Namespace
from weaviate.users.users import UserDB

NAMESPACES_MIN_VERSION = "1.38.0"


def _setup_meta(server: HTTPServer, version: str) -> None:
    """Wire up the minimum endpoints needed for ``connect_to_local`` to succeed.

    Uses ``skip_init_checks=True`` callers; only the version-loading path
    (``/v1/meta``) is exercised. We deliberately avoid the shared
    ``weaviate_mock`` fixture because it pins the version to 1.36, which would
    short-circuit every namespace call with a version-guard error.
    """
    server.expect_request("/v1/meta").respond_with_json({"version": version})
    server.expect_request("/v1/.well-known/openid-configuration").respond_with_response(
        Response(json.dumps({}), status=404)
    )
    server.expect_request("/v1/nodes").respond_with_json(
        {"nodes": [{"gitHash": "ABC", "status": "HEALTHY"}]}
    )


@pytest.fixture(scope="function")
def ns_client(
    ready_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[Tuple[weaviate.WeaviateClient, HTTPServer], None, None]:
    """Client connected against a mock server reporting Weaviate ``1.38.0``."""
    _setup_meta(ready_mock, NAMESPACES_MIN_VERSION)
    client = weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    )
    yield client, ready_mock
    client.close()


@pytest.fixture(scope="function")
def ns_client_old(
    ready_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    """Client connected against a server reporting an older version (1.37.99)."""
    _setup_meta(ready_mock, "1.37.99")
    client = weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC, skip_init_checks=True
    )
    yield client
    client.close()


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_namespaces_create_sends_post_and_parses_response(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``create`` must POST an empty JSON body — the name lives in the URL path.

    Sending anything else (e.g. ``{"name": ...}``) would diverge from the server
    contract and is the kind of refactor that's tempting but breaks on the wire.
    """
    client, server = ns_client
    captured: Dict[str, Any] = {}

    def handler(request: Request) -> Response:
        captured["body"] = json.loads(request.get_data(as_text=True) or "{}")
        return Response(json.dumps({"name": "myns"}), status=201)

    server.expect_request("/v1/namespaces/myns", method="POST").respond_with_handler(handler)

    ns = client.namespaces.create(name="myns")

    assert isinstance(ns, Namespace)
    assert ns.name == "myns"
    assert captured["body"] == {}
    server.check_assertions()


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------


def test_namespaces_get_returns_namespace_when_found(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    client, server = ns_client
    server.expect_request("/v1/namespaces/customer1", method="GET").respond_with_json(
        {"name": "customer1"}, status=200
    )

    ns = client.namespaces.get(name="customer1")

    assert ns is not None
    assert ns.name == "customer1"
    server.check_assertions()


def test_namespaces_get_returns_none_on_404(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``get`` on a missing namespace must return None instead of raising.

    The 404 path is the documented ``does-not-exist`` signal. Without this test,
    swapping ``ok_in=[200, 404]`` for ``[200]`` in ``namespaces/base.py`` would
    silently start raising ``UnexpectedStatusCodeError``.
    """
    client, server = ns_client
    server.expect_request("/v1/namespaces/missing", method="GET").respond_with_response(
        Response(status=404)
    )

    assert client.namespaces.get(name="missing") is None
    server.check_assertions()


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_namespaces_list_all_parses_array(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    client, server = ns_client
    server.expect_request("/v1/namespaces", method="GET").respond_with_json(
        [{"name": "ns1"}, {"name": "ns2"}], status=200
    )

    namespaces = client.namespaces.list_all()

    assert [ns.name for ns in namespaces] == ["ns1", "ns2"]
    server.check_assertions()


def test_namespaces_list_all_handles_null_response(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``list_all`` must return an empty list when the server replies with null.

    The server may return ``null`` (or an empty body) when there are no
    namespaces. The client should yield an empty list, not raise ``TypeError``.
    This guards the ``or []`` fallback in ``namespaces.list_all``.
    """
    client, server = ns_client
    server.expect_request("/v1/namespaces", method="GET").respond_with_response(
        Response(json.dumps(None), status=200, content_type="application/json")
    )

    assert client.namespaces.list_all() == []
    server.check_assertions()


def test_namespaces_list_all_handles_empty_array(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    client, server = ns_client
    server.expect_request("/v1/namespaces", method="GET").respond_with_json([], status=200)

    assert client.namespaces.list_all() == []
    server.check_assertions()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_namespaces_delete_accepts_202(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    client, server = ns_client
    server.expect_request("/v1/namespaces/myns", method="DELETE").respond_with_response(
        Response(status=202)
    )

    # Must not raise; returns None.
    assert client.namespaces.delete(name="myns") is None
    server.check_assertions()


# ---------------------------------------------------------------------------
# Version guard — 1.38.0 minimum
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method_call",
    [
        lambda c: c.namespaces.create(name="x"),
        lambda c: c.namespaces.get(name="x"),
        lambda c: c.namespaces.list_all(),
        lambda c: c.namespaces.delete(name="x"),
    ],
    ids=["create", "get", "list_all", "delete"],
)
def test_namespaces_methods_require_1_38(
    ns_client_old: weaviate.WeaviateClient,
    method_call: Callable[[weaviate.WeaviateClient], object],
) -> None:
    """Every public namespace method must guard with ``check_is_at_least_1_38_0``.

    A new public method that forgets the guard would fail this test, alerting
    the contributor before the request hits an older server and surfaces an
    opaque 404/405.
    """
    with pytest.raises(WeaviateUnsupportedFeatureError):
        method_call(ns_client_old)


# ---------------------------------------------------------------------------
# Namespaced DB user creation
# ---------------------------------------------------------------------------


def test_users_db_create_includes_namespace_in_body(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """When ``namespace`` is provided, the request body must carry it.

    Without this assertion, dropping ``body['namespace'] = namespace`` from
    ``users/base.py`` would compile and pass type-checks but silently break
    namespace-binding on multi-tenant clusters.
    """
    client, server = ns_client
    captured: Dict[str, Any] = {}

    def handler(request: Request) -> Response:
        captured["body"] = json.loads(request.get_data(as_text=True) or "{}")
        return Response(json.dumps({"apikey": "secret-key"}), status=201)

    server.expect_request("/v1/users/db/alice", method="POST").respond_with_handler(handler)

    api_key = client.users.db.create(user_id="alice", namespace="customer1")

    assert api_key == "secret-key"
    assert captured["body"] == {"namespace": "customer1"}
    server.check_assertions()


def test_users_db_create_omits_namespace_when_not_provided(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """The ``namespace`` key must not appear in the body when omitted by the caller.

    Otherwise we'd send ``"namespace": null`` and break older clusters that
    don't recognize the field.
    """
    client, server = ns_client
    captured: Dict[str, Any] = {}

    def handler(request: Request) -> Response:
        captured["body"] = json.loads(request.get_data(as_text=True) or "{}")
        return Response(json.dumps({"apikey": "k"}), status=201)

    server.expect_request("/v1/users/db/bob", method="POST").respond_with_handler(handler)

    client.users.db.create(user_id="bob")

    assert captured["body"] == {}
    server.check_assertions()


def test_users_db_get_populates_namespace_field(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """The ``namespace`` field on the server response must propagate to ``UserDB``.

    Callers rely on ``UserDB.namespace`` to introspect which namespace a user
    belongs to.
    """
    client, server = ns_client
    server.expect_request("/v1/users/db/customer1:alice", method="GET").respond_with_json(
        {
            "userId": "customer1:alice",
            "roles": [],
            "dbUserType": "db_user",
            "active": True,
            "namespace": "customer1",
        },
        status=200,
    )

    user = client.users.db.get(user_id="customer1:alice")

    assert isinstance(user, UserDB)
    assert user.user_id == "customer1:alice"
    assert user.namespace == "customer1"
    server.check_assertions()


def test_users_db_get_namespace_is_none_when_absent(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """A missing ``namespace`` field in the server response must yield ``None``.

    On non-namespace-enabled clusters the server returns no ``namespace`` key.
    ``UserDB.namespace`` must default to ``None`` instead of raising.
    """
    client, server = ns_client
    server.expect_request("/v1/users/db/alice", method="GET").respond_with_json(
        {
            "userId": "alice",
            "roles": [],
            "dbUserType": "db_user",
            "active": True,
        },
        status=200,
    )

    user = client.users.db.get(user_id="alice")

    assert user is not None
    assert user.namespace is None
    server.check_assertions()

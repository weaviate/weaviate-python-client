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
    assert ns.home_node is None
    assert ns.state is None
    assert captured["body"] == {}
    server.check_assertions()


def test_namespaces_create_sends_home_node_when_provided(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """When ``home_node`` is provided, ``create`` must carry it in the request body.

    Dropping ``body['home_node'] = home_node`` would silently ignore the caller's
    placement choice and let the server auto-select instead.
    """
    client, server = ns_client
    captured: Dict[str, Any] = {}

    def handler(request: Request) -> Response:
        captured["body"] = json.loads(request.get_data(as_text=True) or "{}")
        return Response(
            json.dumps({"name": "myns", "home_node": "node1", "state": "active"}),
            status=201,
        )

    server.expect_request("/v1/namespaces/myns", method="POST").respond_with_handler(handler)

    ns = client.namespaces.create(name="myns", home_node="node1")

    assert ns.name == "myns"
    assert ns.home_node == "node1"
    assert ns.state == "active"
    assert captured["body"] == {"home_node": "node1"}
    server.check_assertions()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


def test_namespaces_update_sends_put_and_parses_response(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``update`` must PUT ``{"home_node": ...}`` and return the updated namespace.

    The server requires ``home_node`` in the body; sending anything else (or the
    wrong HTTP verb) would break the modify-placement contract.
    """
    client, server = ns_client
    captured: Dict[str, Any] = {}

    def handler(request: Request) -> Response:
        captured["body"] = json.loads(request.get_data(as_text=True) or "{}")
        return Response(
            json.dumps({"name": "myns", "home_node": "node2", "state": "active"}),
            status=200,
        )

    server.expect_request("/v1/namespaces/myns", method="PUT").respond_with_handler(handler)

    ns = client.namespaces.update(name="myns", home_node="node2")

    assert isinstance(ns, Namespace)
    assert ns.name == "myns"
    assert ns.home_node == "node2"
    assert ns.state == "active"
    assert captured["body"] == {"home_node": "node2"}
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
    assert ns.home_node is None
    assert ns.state is None
    server.check_assertions()


def test_namespaces_get_parses_home_node_and_state(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``get`` must surface the ``home_node`` and ``state`` fields from the response.

    These fields were added to the server's namespace object after the client's
    initial implementation; this guards against the parser silently ignoring them.
    """
    client, server = ns_client
    server.expect_request("/v1/namespaces/customer1", method="GET").respond_with_json(
        {"name": "customer1", "home_node": "node1", "state": "deleting"}, status=200
    )

    ns = client.namespaces.get(name="customer1")

    assert ns is not None
    assert ns.name == "customer1"
    assert ns.home_node == "node1"
    assert ns.state == "deleting"
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


def test_namespaces_list_all_parses_home_node_and_state(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``list_all`` must surface ``home_node`` and ``state`` for each namespace."""
    client, server = ns_client
    server.expect_request("/v1/namespaces", method="GET").respond_with_json(
        [
            {"name": "ns1", "home_node": "node1", "state": "active"},
            {"name": "ns2"},
        ],
        status=200,
    )

    namespaces = client.namespaces.list_all()

    assert namespaces[0].home_node == "node1"
    assert namespaces[0].state == "active"
    assert namespaces[1].home_node is None
    assert namespaces[1].state is None
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
        lambda c: c.namespaces.update(name="x", home_node="n"),
        lambda c: c.namespaces.get(name="x"),
        lambda c: c.namespaces.list_all(),
        lambda c: c.namespaces.delete(name="x"),
    ],
    ids=["create", "update", "get", "list_all", "delete"],
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


def test_users_db_create_qualified_user_id_goes_in_path(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """A namespace-qualified user id must be sent in the URL path, not the body.

    The server derives the namespace from the ``"<namespace>:<user>"`` id in the
    path, so the request body stays empty. This guards against reintroducing a
    ``body['namespace']`` field, which the server no longer accepts.
    """
    client, server = ns_client
    captured: Dict[str, Any] = {}

    def handler(request: Request) -> Response:
        captured["body"] = json.loads(request.get_data(as_text=True) or "{}")
        return Response(json.dumps({"apikey": "secret-key"}), status=201)

    server.expect_request("/v1/users/db/customer1:alice", method="POST").respond_with_handler(
        handler
    )

    api_key = client.users.db.create(user_id="customer1:alice")

    assert api_key == "secret-key"
    assert captured["body"] == {}
    server.check_assertions()


def test_users_db_create_posts_empty_body(
    ns_client: Tuple[weaviate.WeaviateClient, HTTPServer],
) -> None:
    """``create`` must POST an empty body — there is no separate ``namespace`` field.

    Sending anything else (e.g. a stray ``namespace`` key) would diverge from the
    server contract, which expects only the (possibly qualified) id in the path.
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

"""CPython tests for the Emscripten guards, grpc-web routing and grpc-web diagnostics."""

import asyncio
import pathlib
import subprocess
import sys
import textwrap

import grpc
import pytest
from grpc.aio import AioRpcError, Metadata

from weaviate import WeaviateClient
from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.connect.base import ConnectionParams
from weaviate.connect.v4 import _ConnectionBase
from weaviate.embedded import _EmbeddedBase
from weaviate.exceptions import (
    WeaviateBatchStreamError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
)
from weaviate.util import _ServerVersion


def test_embedded_raises_explicit_error_under_emscripten(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="WebAssembly/Pyodide"):
        _EmbeddedBase.check_supported_platform()


def test_sync_client_construction_raises_async_only_under_emscripten(monkeypatch) -> None:
    # fails at construction, not with a ConnectError on the first REST call
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="async client"):
        WeaviateClient(connection_params=ConnectionParams.from_url("http://localhost:8080", 50051))


def test_batch_stream_fails_fast_when_grpc_web_shim_active(monkeypatch) -> None:
    # _start must raise before any background task exists
    monkeypatch.setattr(grpc, "__weaviate_client_web_shim__", True, raising=False)
    batch = object.__new__(_BatchBaseAsync)  # the guard runs before any attribute access
    with pytest.raises(WeaviateBatchStreamError, match="insert_many"):
        asyncio.run(batch._start())


# --- grpc-web diagnostics -------------------------------------------------------------


def _connection(prefix=None) -> _ConnectionBase:
    conn = object.__new__(_ConnectionBase)
    conn._client = None
    conn._grpc_channel = None
    conn._weaviate_version = _ServerVersion.from_string("1.36.0")
    conn._connection_params = ConnectionParams.from_url(
        "http://localhost:8080",
        grpc_port=8080 if prefix else 50051,
        grpc_path_prefix=prefix,
    )
    return conn


def _ping_exception(conn: _ConnectionBase, error: Exception) -> None:
    getattr(conn, "_ConnectionBase__handle_ping_exception")(error)  # noqa: B009


def test_grpc_web_404_names_the_two_real_causes_and_drops_firewall_advice() -> None:
    conn = _connection(prefix="/grpc-web")
    error = AioRpcError(
        grpc.StatusCode.UNIMPLEMENTED,
        Metadata(),
        Metadata(),
        details="HTTP 404 for /grpc-web/grpc.health.v1.Health/Check: 404 page not found",
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    assert "firewall" not in msg
    assert "port (localhost:8080) are correct" not in msg
    assert "UNIMPLEMENTED" in msg  # the real code, not swallowed
    assert "HTTP 404 for /grpc-web/grpc.health.v1.Health/Check" in msg  # ... and details
    assert "/grpc-web" in msg  # the prefix that was actually used
    assert "1.38.3" in msg  # candidate 1: server too old ...
    assert "v1.36.0" in msg  # ... shown against the observed server version
    assert "/v1/grpc-web" in msg  # candidate 2: wrong prefix


def test_grpc_web_genuine_unimplemented_is_not_diagnosed_as_a_wrong_path() -> None:
    # a routed grpc-web endpoint can itself return UNIMPLEMENTED (e.g. the health
    # service is missing); only the channel's synthetic HTTP 404/405 means "not routed"
    conn = _connection(prefix="/grpc-web")
    error = AioRpcError(
        grpc.StatusCode.UNIMPLEMENTED, Metadata(), Metadata(), details="Method not implemented"
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    assert "too old" not in msg
    assert "1.38.3" not in msg
    assert "UNIMPLEMENTED" in msg  # the real status is still reported
    assert "skip_init_checks=True" in msg  # the generic grpc-web advice applies


def test_grpc_web_non_404_error_still_omits_the_native_port_advice() -> None:
    conn = _connection(prefix="/grpc-web")
    error = AioRpcError(
        grpc.StatusCode.UNAVAILABLE, Metadata(), Metadata(), details="HTTP 502 for /grpc-web/..."
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    assert "firewall" not in msg
    assert "UNAVAILABLE" in msg
    assert "HTTP 502" in msg
    assert "skip_init_checks=True" in msg  # the still-useful advice is kept


def test_native_grpc_message_keeps_its_advice_and_gains_the_real_status() -> None:
    conn = _connection()
    error = AioRpcError(
        grpc.StatusCode.UNAVAILABLE, Metadata(), Metadata(), details="failed to connect"
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    # unchanged guidance for native gRPC ...
    assert "The gRPC traffic at the specified port is blocked by a firewall." in msg
    assert "Please check that the server address and port (localhost:50051) are correct." in msg
    # ... plus the call's status and details
    assert "UNAVAILABLE" in msg
    assert "failed to connect" in msg


def test_non_grpc_ping_error_is_still_reported() -> None:
    # not every ping failure is an RpcError; those must not lose the generic advice
    conn = _connection()
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, ValueError("boom"))
    assert "blocked by a firewall" in str(excinfo.value)


# --- grpc-web routing under Emscripten ------------------------------------------------

GRPC_WEB_PREFIX = "/v1/grpc-web"


@pytest.fixture
def emscripten(monkeypatch):
    """Fake Emscripten, with the grpc shim marked active.

    Under real Pyodide ``import weaviate`` installs the shim itself; here only the
    routing decision is under test, not the environment check that guards it.
    """
    import weaviate.connect.base as base_mod

    monkeypatch.setattr(sys, "platform", "emscripten")
    monkeypatch.setattr(base_mod.grpc, "__weaviate_client_web_shim__", True, raising=False)


def _params(client) -> ConnectionParams:
    return client._connection._connection_params


def _assert_grpc_rides_rest(client) -> None:
    params = _params(client)
    assert params.grpc.model_dump() == params.http.model_dump()
    assert params._grpc_web_path_prefix == GRPC_WEB_PREFIX
    assert params._grpc_target == f"{params.http.host}:{params.http.port}"


def test_use_async_with_local_routes_grpc_to_rest_under_emscripten(emscripten) -> None:
    import weaviate

    _assert_grpc_rides_rest(weaviate.use_async_with_local(host="localhost", port=8290))
    assert _params(weaviate.use_async_with_local()).model_dump() == {
        "http": {"host": "localhost", "port": 8080, "secure": False},
        "grpc": {"host": "localhost", "port": 8080, "secure": False},
        "grpc_path_prefix": GRPC_WEB_PREFIX,
    }


def test_use_async_with_weaviate_cloud_routes_grpc_to_the_cluster_host(emscripten) -> None:
    # Weaviate Cloud serves grpc-web on the cluster's own REST endpoint, not on grpc-<cluster>
    import weaviate

    client = weaviate.use_async_with_weaviate_cloud("abc.something.weaviate.cloud", None)
    _assert_grpc_rides_rest(client)
    assert _params(client).model_dump() == {
        "http": {"host": "abc.something.weaviate.cloud", "port": 443, "secure": True},
        "grpc": {"host": "abc.something.weaviate.cloud", "port": 443, "secure": True},
        "grpc_path_prefix": GRPC_WEB_PREFIX,
    }


def test_use_async_with_custom_routes_grpc_to_rest_under_emscripten(emscripten) -> None:
    import weaviate

    _assert_grpc_rides_rest(
        weaviate.use_async_with_custom(
            http_host="wv.example.com",
            http_port=443,
            http_secure=True,
            grpc_host="wv.example.com",
            grpc_port=443,
            grpc_secure=True,
        )
    )


def test_matching_grpc_arguments_are_not_warned_about(emscripten, recwarn) -> None:
    # gRPC arguments equal to the HTTP ones: nothing is replaced, so no warning
    import weaviate

    weaviate.use_async_with_custom(
        http_host="localhost",
        http_port=8290,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=8290,
        grpc_secure=False,
    )
    weaviate.use_async_with_local(port=8290)
    weaviate.use_async_with_weaviate_cloud("abc.something.weaviate.cloud", None)
    assert [str(w.message) for w in recwarn] == []


def test_overridden_grpc_arguments_are_warned_about(emscripten) -> None:
    # a replaced caller endpoint must warn
    import weaviate

    with pytest.warns(UserWarning, match="Con006") as record:
        client = weaviate.use_async_with_custom(
            http_host="localhost",
            http_port=8080,
            http_secure=False,
            grpc_host="grpc.example.com",
            grpc_port=50051,
            grpc_secure=True,
        )
    msg = str(record[0].message)
    assert "grpc.example.com:50051" in msg  # what was discarded ...
    assert "localhost:8080" in msg  # ... and what is used instead
    assert "WebAssembly" in msg  # ... and why
    _assert_grpc_rides_rest(client)


def test_a_secure_only_grpc_mismatch_is_visible_in_the_warning(emscripten) -> None:
    # host:port alone would print two identical endpoints; the scheme shows what differed
    import weaviate

    with pytest.warns(UserWarning, match="Con006") as record:
        client = weaviate.use_async_with_custom(
            http_host="localhost",
            http_port=8080,
            http_secure=False,
            grpc_host="localhost",
            grpc_port=8080,
            grpc_secure=True,
        )
    msg = str(record[0].message)
    assert "grpcs://localhost:8080" in msg  # what was discarded ...
    assert "grpc://localhost:8080" in msg  # ... and what is used instead
    _assert_grpc_rides_rest(client)


def test_an_explicit_local_grpc_port_is_warned_about_but_the_default_is_not(emscripten) -> None:
    import weaviate

    with pytest.warns(UserWarning, match="Con006"):
        client = weaviate.use_async_with_local(port=8080, grpc_port=8081)
    _assert_grpc_rides_rest(client)


# --- the single-import hook (weaviate/__init__.py) ------------------------------------
#
# The import hook replaces sys.modules["grpc"], so each scenario runs in a fresh subprocess.
# The success path runs in ci/pyodide-e2e/units.mjs.

_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[1])

# CPython derives the _sysconfigdata module name from sys.platform on first use, so a
# faked platform breaks any later sysconfig lookup (pydantic imports zoneinfo, which
# calls sysconfig.get_config_var). Prime the cache before faking.
_PRIME_SYSCONFIG = """
import sysconfig

sysconfig.get_config_vars()
"""


def _run_hook_scenario(
    body: str, *, prelude: str = "", path_entry: str = _REPO_ROOT, no_site: bool = False
) -> subprocess.CompletedProcess:
    # -I -S: skip site-packages entirely (plain -I still processes the venv's .pth
    # files), so nothing pip-installed is importable — only stdlib plus `path_entry`.
    interp = [sys.executable, "-I", "-S"] if no_site else [sys.executable]
    script = f"import sys\nsys.path.insert(0, {path_entry!r})\n" + prelude + textwrap.dedent(body)
    return subprocess.run([*interp, "-c", script], capture_output=True, text=True)


def test_bare_import_without_companion_raises_clear_import_error() -> None:
    # No site-packages, so neither weaviate_client_web nor grpcio is importable; the repo
    # root goes on sys.path so the weaviate package itself is still found.
    result = _run_hook_scenario(
        """
        sys.platform = "emscripten"
        try:
            import weaviate
        except ImportError as e:
            assert "weaviate-client-web" in str(e), str(e)
            assert "weaviate-client[grpc-web]" in str(e), str(e)
            assert "WebAssembly/Pyodide" in str(e), str(e)
            print("OK")
        else:
            raise AssertionError("expected ImportError without the companion")
        """,
        no_site=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_bare_import_with_grpc_present_falls_through_silently() -> None:
    # weaviate_client_web blocked but a real grpc importable (grpcio in the dev env): the
    # hook falls through and leaves the normal import path untouched
    result = _run_hook_scenario(
        prelude=_PRIME_SYSCONFIG,
        body="""
        sys.platform = "emscripten"
        sys.modules["weaviate_client_web"] = None  # makes its import raise ImportError

        import weaviate
        import grpc

        assert not getattr(grpc, "__weaviate_client_web_shim__", False)
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_bare_import_with_broken_companion_surfaces_its_own_error(tmp_path) -> None:
    # an installed weaviate-client-web that fails to import surfaces its own error, not the
    # install hint
    fake_pkg = tmp_path / "weaviate_client_web"
    fake_pkg.mkdir()
    (fake_pkg / "__init__.py").write_text(
        "raise ModuleNotFoundError(\"No module named 'anyio'\", name='anyio')\n"
    )
    result = _run_hook_scenario(
        prelude=_PRIME_SYSCONFIG,
        body="""
        sys.platform = "emscripten"
        try:
            import weaviate
        except ImportError as e:
            assert e.name == "anyio", (e.name, str(e))
            assert "anyio" in str(e), str(e)
            assert "grpc-web" not in str(e), str(e)
            print("OK")
        else:
            raise AssertionError("expected the companion's own ImportError to surface")
        """,
        path_entry=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout

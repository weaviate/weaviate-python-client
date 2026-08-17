"""Tests for the single-import hook in the base client (``weaviate/__init__.py``).

The hook fires on ``sys.platform == "emscripten"`` and (via the companion's bootstrap)
replaces ``sys.modules['grpc']`` process-wide, so each scenario runs in a fresh
subprocess with the platform faked before ``import weaviate`` — the same pattern as
test_shim_install.py / test_httpx_fetch.py's install tests.
"""

import pathlib
import subprocess
import sys
import textwrap

_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "src")
_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[3])

# CPython derives the _sysconfigdata module name from sys.platform on first use, so a
# faked platform breaks any later sysconfig lookup (pydantic imports zoneinfo, which
# calls sysconfig.get_config_var). Prime the cache before faking.
_PRIME_SYSCONFIG = """
import sysconfig

sysconfig.get_config_vars()
"""


def _run(
    body: str, *, prelude: str = "", path_entry: str = _SRC, no_site: bool = False
) -> subprocess.CompletedProcess:
    # -I -S: skip site-packages entirely (plain -I still processes the venv's .pth
    # files), so nothing pip-installed is importable — only stdlib plus `path_entry`.
    interp = [sys.executable, "-I", "-S"] if no_site else [sys.executable]
    script = f"import sys\nsys.path.insert(0, {path_entry!r})\n" + prelude + textwrap.dedent(body)
    return subprocess.run([*interp, "-c", script], capture_output=True, text=True)


def test_bare_import_weaviate_installs_shim_under_emscripten():
    result = _run(
        prelude=_PRIME_SYSCONFIG,
        body="""
        import importlib.machinery, types

        sys.platform = "emscripten"
        # Pretend httpx is Pyodide's jsfetch build so the companion's bootstrap skips
        # the fetch-transport install (there is no pyodide module on CPython).
        fake = types.ModuleType("httpx._transports.jsfetch")
        fake.__spec__ = importlib.machinery.ModuleSpec("httpx._transports.jsfetch", loader=None)
        sys.modules["httpx._transports.jsfetch"] = fake

        import weaviate  # the ONLY weaviate-side import: must bootstrap the companion

        assert "weaviate_grpc_web" in sys.modules, "hook did not import the companion"
        import weaviate_grpc_web
        assert weaviate_grpc_web.is_installed()
        import grpc
        assert getattr(grpc, "__weaviate_grpc_web_shim__", False) is True
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_bare_import_without_companion_raises_clear_import_error():
    # No site-packages, so neither weaviate_grpc_web nor grpcio is importable; the repo
    # root goes on sys.path so the weaviate package itself is still found.
    result = _run(
        """
        sys.platform = "emscripten"
        try:
            import weaviate
        except ImportError as e:
            assert "weaviate-python-grpc-web" in str(e), str(e)
            assert "WebAssembly/Pyodide" in str(e), str(e)
            print("OK")
        else:
            raise AssertionError("expected ImportError without the companion")
        """,
        path_entry=_REPO_ROOT,
        no_site=True,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_bare_import_with_grpc_present_falls_through_silently():
    # Companion blocked but a real grpc IS importable (grpcio in the dev env): the hook
    # must fall through and leave the normal import path untouched.
    result = _run(
        prelude=_PRIME_SYSCONFIG,
        body="""
        sys.platform = "emscripten"
        sys.modules["weaviate_grpc_web"] = None  # makes its import raise ImportError

        import weaviate
        import grpc

        assert not getattr(grpc, "__weaviate_grpc_web_shim__", False)
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout

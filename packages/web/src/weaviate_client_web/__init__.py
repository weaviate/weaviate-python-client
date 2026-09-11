"""grpc-web / WASM transport for the Weaviate Python client.

Under Pyodide/Emscripten there is no ``grpcio`` wheel. Importing this package installs a
pure-Python ``grpc`` shim into ``sys.modules`` (and forces the pure-Python protobuf
runtime) so that the subsequent ``import weaviate`` succeeds and its async gRPC data path
runs over grpc-web (``fetch``) instead of HTTP/2 sockets; REST runs through the package's
own ``fetch``-based httpx transport.

Usage under Pyodide against Weaviate >= 1.38.3, which serves grpc-web on its REST port
under ``/v1/grpc-web`` (with this package installed, a bare ``import weaviate`` suffices —
the base client imports this package itself under Emscripten before anything else)::

    import weaviate

    client = weaviate.use_async_with_local(port=8080)
    await client.connect()

There is nothing to select. Under Emscripten ``use_async_with_local``,
``use_async_with_weaviate_cloud`` and ``use_async_with_custom`` all pin gRPC to the REST
endpoint under ``/v1/grpc-web``, because native gRPC is impossible there — the same
contract as the TypeScript ``@weaviate/web`` client. ``use_async_with_custom`` still
requires ``grpc_host``/``grpc_port``/``grpc_secure``; give it the HTTP values, or it
warns that it overrode them.

An explicit ``import weaviate_client_web`` before ``import weaviate`` also works and
remains the explicit form. The shim is installed automatically only under Emscripten, so
importing this package on a normal CPython install never clobbers a real, working
``grpcio``. Async clients only — the synchronous client is not supported in the browser.
"""

import os
import sys

from ._shim import StatusCode, install, is_installed

__all__ = [
    "install",
    "is_installed",
    "install_fetch_transport",
    "uninstall_fetch_transport",
    "is_fetch_transport_installed",
    "set_sender",
    "make_httpx_sender",
    "GrpcWebChannel",
    "StatusCode",
]


def _bootstrap() -> None:
    if sys.platform == "emscripten":
        # The pure-Python protobuf runtime always works; the upb C-extension may not be
        # present. Set before ``import weaviate`` (which imports protobuf) so it takes
        # effect. ``setdefault`` lets a user override it explicitly.
        os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
        install()
        # The REST path needs fetch too: httpx/httpcore open raw sockets, which do
        # not exist under WASM. Imported lazily so CPython imports stay light.
        from ._httpx_fetch import install_fetch_transport

        install_fetch_transport()


_bootstrap()

# Imported after the bootstrap. These modules pull their grpc base classes directly from
# ``._shim`` (not via ``sys.modules['grpc']``), so importing them is safe regardless of
# whether the shim was installed.
from ._channel import GrpcWebChannel, set_sender  # noqa: E402
from ._httpx_fetch import (  # noqa: E402
    install_fetch_transport,
    is_fetch_transport_installed,
    uninstall_fetch_transport,
)
from ._sender import make_httpx_sender  # noqa: E402

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
remains the explicit form. This package is defined for its environment: it imports
``pyodide`` at module scope, so it is only importable under Emscripten/Pyodide — on
CPython the base client never imports it, and the ``weaviate-client[grpc-web]`` extra
does not install it there (platform marker). Async clients only — the synchronous client
is not supported in the browser.
"""

import os
import sys

from ._channel import GrpcWebChannel, set_sender
from ._httpx_fetch import (
    install_fetch_transport,
    is_fetch_transport_installed,
    uninstall_fetch_transport,
)
from ._shim import StatusCode, install, is_installed

__all__ = [
    "install",
    "is_installed",
    "install_fetch_transport",
    "uninstall_fetch_transport",
    "is_fetch_transport_installed",
    "set_sender",
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
        # not exist under WASM.
        install_fetch_transport()


_bootstrap()

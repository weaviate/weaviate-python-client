"""grpc-web / WASM transport for the Weaviate Python client.

Under Pyodide/Emscripten there is no ``grpcio`` wheel. Importing this package installs a
pure-Python ``grpc`` shim into ``sys.modules`` (and forces the pure-Python protobuf
runtime) so that the subsequent ``import weaviate`` succeeds and its async gRPC data path
runs over grpc-web (``fetch``) instead of HTTP/2 sockets.

Usage under Pyodide::

    import weaviate_grpc_web   # installs the grpc shim (no-op off Emscripten)
    import weaviate

    client = weaviate.use_async_with_local(skip_init_checks=True)
    await client.connect()

The shim is installed automatically only under Emscripten, so importing this package on a
normal CPython install never clobbers a real, working ``grpcio``. Async clients only —
the synchronous client is not supported in the browser.
"""

import os
import sys

from ._shim import StatusCode, install, is_installed

__all__ = [
    "install",
    "is_installed",
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


_bootstrap()

# Imported after the bootstrap. These modules pull their grpc base classes directly from
# ``._shim`` (not via ``sys.modules['grpc']``), so importing them is safe regardless of
# whether the shim was installed.
from ._channel import GrpcWebChannel, set_sender  # noqa: E402
from ._sender import make_httpx_sender  # noqa: E402

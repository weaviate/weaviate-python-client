"""grpc-web and fetch transports for the Weaviate Python client under Pyodide.

Importing this package (``import weaviate`` does so under Emscripten) installs a pure-Python
``grpc`` shim and a fetch-based httpx transport. It imports only under Pyodide and supports
async clients only.
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
        # upb may be missing under Pyodide; set before protobuf is imported (setdefault
        # keeps a user override).
        os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
        install()
        # httpcore needs sockets, so REST also goes through fetch.
        install_fetch_transport()


_bootstrap()

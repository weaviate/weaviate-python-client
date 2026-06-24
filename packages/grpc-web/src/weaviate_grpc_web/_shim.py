"""A minimal pure-Python stand-in for the ``grpc`` API surface ``weaviate-client`` uses.

It covers what ``weaviate-client`` touches at import time and on the async unary data
path. It is installed into ``sys.modules`` (as ``grpc``, ``grpc.aio``, ``grpc._utilities``,
``grpc.aio._typing``, ``grpc.experimental``) *before* ``import weaviate`` so the client
loads under Pyodide/Emscripten, where the real ``grpcio`` C-extension wheel does not
exist. The shim satisfies two contracts at once:

1. **Import surface** — every ``import grpc`` / ``from grpc(.aio) import ...`` executed
   while ``weaviate`` and its generated ``*_pb2_grpc`` stubs are imported
   (``weaviate/config.py:4-5``, ``exceptions.py:7-8``, ``retry.py:5-6``,
   ``connect/base.py:5-8``, ``connect/v4.py:24,29-32``, and the v6300 stub's
   ``grpc.__version__`` / ``grpc._utilities.first_version_is_lower`` version gate).
2. **Runtime type contract** — :class:`AioChannel` becomes ``grpc.aio.Channel`` so the
   real grpc-web channel (which subclasses it) passes the
   ``isinstance(..., grpc.aio.Channel)`` assertions in ``connect/v4.py`` (lines 722,
   1241); :class:`AioRpcError` is the error the client catches and inspects via
   ``.code()`` / ``.details()`` (``exceptions.py:62-76``, ``retry.py:30-31``).
"""

import enum
import sys
import types
from typing import Any, Optional

# grpcio reports 1.72.1 as the version that the v6300 generated stub requires; matching
# it makes the stub's import-time version gate pass. See weaviate/proto/v1/__init__.py.
FAKE_GRPC_VERSION = "1.72.1"

_SHIM_MARKER = "__weaviate_grpc_web_shim__"


class StatusCode(enum.Enum):
    """Mirror of ``grpc.StatusCode``.

    ``value`` is the canonical ``(int, str)`` tuple, matching grpcio so ``code.value[0]``
    / ``code.value[1]`` (``exceptions.py:63,66``) and ``code.name``
    (``connect/v4.py:1189``) behave identically.
    """

    OK = (0, "ok")
    CANCELLED = (1, "cancelled")
    UNKNOWN = (2, "unknown")
    INVALID_ARGUMENT = (3, "invalid argument")
    DEADLINE_EXCEEDED = (4, "deadline exceeded")
    NOT_FOUND = (5, "not found")
    ALREADY_EXISTS = (6, "already exists")
    PERMISSION_DENIED = (7, "permission denied")
    RESOURCE_EXHAUSTED = (8, "resource exhausted")
    FAILED_PRECONDITION = (9, "failed precondition")
    ABORTED = (10, "aborted")
    OUT_OF_RANGE = (11, "out of range")
    UNIMPLEMENTED = (12, "unimplemented")
    INTERNAL = (13, "internal")
    UNAVAILABLE = (14, "unavailable")
    DATA_LOSS = (15, "data loss")
    UNAUTHENTICATED = (16, "unauthenticated")


_BY_NUMBER = {member.value[0]: member for member in StatusCode}


def status_from_int(code: int) -> StatusCode:
    """Map a numeric grpc-status to a :class:`StatusCode` (``UNKNOWN`` if unmapped)."""
    return _BY_NUMBER.get(code, StatusCode.UNKNOWN)


class RpcError(Exception):
    """Stand-in for ``grpc.RpcError`` (imported by ``retry.py``)."""


class Call:
    """Stand-in for ``grpc.Call`` (imported by ``exceptions.py`` / ``retry.py``).

    Only used for ``isinstance``/type-import purposes; the async-only WASM path raises
    :class:`AioRpcError`, never a sync ``Call``.
    """

    def code(self) -> StatusCode:  # pragma: no cover - never instantiated under WASM
        raise NotImplementedError

    def details(self) -> str:  # pragma: no cover
        raise NotImplementedError


class AioRpcError(RpcError):
    """Stand-in for ``grpc.aio.AioRpcError``.

    Raised by the grpc-web multicallable on a non-OK status; exposes the same
    ``code()`` / ``details()`` surface the client uses.
    """

    def __init__(
        self,
        code: StatusCode,
        initial_metadata: Any = None,
        trailing_metadata: Any = None,
        details: str = "",
        debug_error_string: Optional[str] = None,
    ) -> None:
        self._code = code
        self._details = details
        self._initial_metadata = initial_metadata
        self._trailing_metadata = trailing_metadata
        self._debug_error_string = debug_error_string
        super().__init__(f"<AioRpcError code={code.name} details={details!r}>")

    def code(self) -> StatusCode:
        return self._code

    def details(self) -> str:
        return self._details

    def initial_metadata(self) -> Any:
        return self._initial_metadata

    def trailing_metadata(self) -> Any:
        return self._trailing_metadata

    def debug_error_string(self) -> Optional[str]:
        return self._debug_error_string


class StreamStreamCall:
    """Stand-in for ``grpc.aio.StreamStreamCall`` (imported as a type at ``v4.py:31``)."""


class ChannelCredentials:
    """Stand-in for ``grpc.ChannelCredentials`` (imported by ``config.py:4``)."""


def ssl_channel_credentials(*_args: Any, **_kwargs: Any) -> ChannelCredentials:
    return ChannelCredentials()


class SyncChannel:
    """Stand-in for ``grpc.Channel`` (sync).

    Never instantiated under WASM — the sync channel factory raises (the WASM transport
    is async-only).
    """


class AioChannel:
    """Become ``grpc.aio.Channel``.

    The grpc-web channel subclasses this so the ``isinstance(..., grpc.aio.Channel)``
    assertions in ``connect/v4.py`` hold.
    """


def first_version_is_lower(_version: str, _other: str) -> bool:
    """Stand-in for ``grpc._utilities.first_version_is_lower``.

    Returning ``False`` makes the v6300 stub's version gate
    (``weaviate_pb2_grpc.py:17-29``) pass.
    """
    return False


_ASYNC_ONLY_MESSAGE = (
    "weaviate-python-grpc-web provides an asynchronous-only gRPC transport under "
    "WebAssembly/Pyodide. Use an async client (weaviate.use_async_with_local / "
    "use_async_with_weaviate_cloud / use_async_with_custom, or WeaviateAsyncClient); "
    "the synchronous client is not supported in the browser."
)


def _sync_channel_unsupported(*_args: Any, **_kwargs: Any) -> "AioChannel":
    raise RuntimeError(_ASYNC_ONLY_MESSAGE)


def _path_prefix_from_options(options: Any) -> str:
    """Extract the ``("grpc-web.path_prefix", prefix)`` channel option, or "" if absent."""
    for item in options or ():
        if isinstance(item, (tuple, list)) and len(item) == 2 and item[0] == "grpc-web.path_prefix":
            return item[1] or ""
    return ""


def _aio_secure_channel(
    target: Optional[str] = None, credentials: Any = None, options: Any = None, **_kw: Any
) -> AioChannel:
    from ._channel import GrpcWebChannel

    return GrpcWebChannel(
        target=target,
        secure=True,
        options=options,
        path_prefix=_path_prefix_from_options(options),
    )


def _aio_insecure_channel(
    target: Optional[str] = None, options: Any = None, **_kw: Any
) -> AioChannel:
    from ._channel import GrpcWebChannel

    return GrpcWebChannel(
        target=target,
        secure=False,
        options=options,
        path_prefix=_path_prefix_from_options(options),
    )


def _noop(*_args: Any, **_kwargs: Any) -> None:
    """Inert stand-in for imported-but-unused server-side stub-registration helpers.

    e.g. ``grpc.unary_unary_rpc_method_handler``: imported by generated ``*_pb2_grpc``
    code, never called by the client.
    """
    return None


def is_installed() -> bool:
    return getattr(sys.modules.get("grpc"), _SHIM_MARKER, False) is True


def install(force: bool = False) -> bool:
    """Install the shim into ``sys.modules`` as ``grpc`` and submodules.

    On normal platforms this is a no-op unless ``force=True`` — we must never clobber a
    real, working ``grpcio``. Under Emscripten the bootstrap calls this automatically.
    Returns ``True`` if the shim is in place afterwards.
    """
    if not force and sys.platform != "emscripten":
        return False
    if is_installed():
        return True

    # Modules are populated via __dict__.update — dynamic module synthesis, so static
    # type checkers do not flag each attribute assignment.
    utilities = types.ModuleType("grpc._utilities")
    utilities.__dict__["first_version_is_lower"] = first_version_is_lower

    experimental = types.ModuleType("grpc.experimental")
    experimental.__dict__.update(unary_unary=_noop, stream_stream=_noop)

    aio_typing = types.ModuleType("grpc.aio._typing")
    aio_typing.__dict__["ChannelArgumentType"] = Any

    aio = types.ModuleType("grpc.aio")
    aio.__dict__.update(
        Channel=AioChannel,
        AioRpcError=AioRpcError,
        StreamStreamCall=StreamStreamCall,
        secure_channel=_aio_secure_channel,
        insecure_channel=_aio_insecure_channel,
        _typing=aio_typing,
    )

    grpc_mod = types.ModuleType("grpc")
    grpc_mod.__dict__.update(
        {
            "__version__": FAKE_GRPC_VERSION,
            _SHIM_MARKER: True,
            "StatusCode": StatusCode,
            "RpcError": RpcError,
            "Call": Call,
            "Channel": SyncChannel,
            "ChannelCredentials": ChannelCredentials,
            "ssl_channel_credentials": ssl_channel_credentials,
            "secure_channel": _sync_channel_unsupported,
            "insecure_channel": _sync_channel_unsupported,
            # Imported (never called) by generated *_pb2_grpc servicer/registration code.
            "unary_unary_rpc_method_handler": _noop,
            "stream_stream_rpc_method_handler": _noop,
            "unary_stream_rpc_method_handler": _noop,
            "stream_unary_rpc_method_handler": _noop,
            "method_handlers_generic_handler": _noop,
            "_utilities": utilities,
            "experimental": experimental,
            "aio": aio,
        }
    )

    sys.modules["grpc"] = grpc_mod
    sys.modules["grpc._utilities"] = utilities
    sys.modules["grpc.experimental"] = experimental
    sys.modules["grpc.aio"] = aio
    sys.modules["grpc.aio._typing"] = aio_typing
    return True

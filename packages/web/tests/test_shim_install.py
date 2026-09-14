"""grpc shim tests, against this interpreter's real installation.

Run inside Pyodide via ``ci/pyodide-e2e/units.mjs``: importing ``weaviate_client_web``
bootstrapped the shim, so ``sys.modules['grpc']`` here IS the shim. Bootstrap scenarios
that need a clean import state (a bare ``import weaviate``, a missing or broken
companion) live in ``units.mjs``, one fresh interpreter each.
"""

import struct

from harness import raises

import weaviate_client_web
from weaviate_client_web import GrpcWebChannel, set_sender
from weaviate_client_web._sender import pyfetch_sender
from weaviate_client_web._shim import FAKE_GRPC_VERSION


def _frame(payload: bytes, flag: int = 0x00) -> bytes:
    return struct.pack(">BI", flag, len(payload)) + payload


def test_import_weaviate_under_shim():
    import grpc

    assert weaviate_client_web.is_installed()
    assert getattr(grpc, "__weaviate_client_web_shim__", False) is True
    assert grpc.__version__ == FAKE_GRPC_VERSION
    assert grpc._utilities.first_version_is_lower("1.0.0", "2.0.0") is False  # type: ignore[attr-defined]
    from grpc.aio._typing import ChannelArgumentType  # noqa: F401

    import weaviate  # noqa: F401  # must not raise even though grpcio is shimmed
    from weaviate.proto.v1 import weaviate_pb2_grpc

    ch = GrpcWebChannel("localhost:50051", secure=False)
    stub = weaviate_pb2_grpc.WeaviateStub(ch)
    assert stub.Search is not None
    assert stub.BatchObjects is not None
    assert stub.BatchDelete is not None
    assert isinstance(ch, grpc.aio.Channel)


def test_sync_channel_factory_raises_async_only():
    import grpc

    with raises(RuntimeError) as excinfo:
        grpc.insecure_channel("localhost:50051")
    assert "async" in str(excinfo.value).lower()


async def test_real_proto_unary_round_trip_under_shim():
    from weaviate.proto.v1 import tenants_pb2, weaviate_pb2_grpc

    reply = tenants_pb2.TenantsGetReply()
    payload = reply.SerializeToString()
    body = _frame(payload) + _frame(b"grpc-status:0\r\n", 0x80)

    async def sender(url, headers, body_in, timeout):
        assert headers["authorization"] == "Bearer k"
        assert url.endswith("/weaviate.v1.Weaviate/TenantsGet")
        return 200, {}, body

    set_sender(sender)
    try:
        ch = GrpcWebChannel("localhost:50051", secure=False)
        stub = weaviate_pb2_grpc.WeaviateStub(ch)
        res = await stub.TenantsGet(
            tenants_pb2.TenantsGetRequest(),
            metadata=[("authorization", "Bearer k")],
            timeout=5,
        )
        assert isinstance(res, tenants_pb2.TenantsGetReply)
    finally:
        set_sender(pyfetch_sender)


def test_fake_grpc_version_matches_base_fallback():
    # The shim advertises FAKE_GRPC_VERSION as grpc.__version__ and the base package
    # falls back to _GRPCIO_FALLBACK_VERSION under Emscripten — the vendored stubs'
    # version gates see both, so they must never drift apart.
    from weaviate.proto.v1 import _GRPCIO_FALLBACK_VERSION

    assert FAKE_GRPC_VERSION == _GRPCIO_FALLBACK_VERSION

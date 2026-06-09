"""Shim/import tests.

Installing the shim replaces ``sys.modules['grpc']`` process-wide, so each scenario runs
in a fresh subprocess to avoid clobbering the real ``grpc`` used by the rest of the suite.
"""

import pathlib
import subprocess
import sys
import textwrap

_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "src")


def _run(body: str) -> subprocess.CompletedProcess:
    script = f"import sys\nsys.path.insert(0, {_SRC!r})\n" + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)


def test_import_weaviate_under_shim():
    result = _run(
        """
        import weaviate_grpc_web
        assert weaviate_grpc_web.install(force=True) is True
        assert weaviate_grpc_web.is_installed()

        import grpc
        assert getattr(grpc, "__weaviate_grpc_web_shim__", False) is True
        assert grpc.__version__ == "1.72.1"
        assert grpc._utilities.first_version_is_lower("1.0.0", "2.0.0") is False
        from grpc.aio._typing import ChannelArgumentType  # noqa: F401

        import weaviate  # must not raise even though grpcio is shimmed
        from weaviate.proto.v1 import weaviate_pb2_grpc
        from weaviate_grpc_web import GrpcWebChannel

        ch = GrpcWebChannel("localhost:50051", secure=False)
        stub = weaviate_pb2_grpc.WeaviateStub(ch)
        assert stub.Search is not None
        assert stub.BatchObjects is not None
        assert stub.BatchDelete is not None
        assert isinstance(ch, grpc.aio.Channel)
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_sync_channel_factory_raises_async_only():
    result = _run(
        """
        import weaviate_grpc_web
        weaviate_grpc_web.install(force=True)
        import grpc
        try:
            grpc.insecure_channel("localhost:50051")
        except RuntimeError as exc:
            assert "async" in str(exc).lower()
            print("OK")
        else:
            raise AssertionError("expected sync channel factory to raise")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_real_proto_unary_round_trip_under_shim():
    result = _run(
        """
        import asyncio
        import struct
        import weaviate_grpc_web
        weaviate_grpc_web.install(force=True)

        import weaviate  # noqa: F401
        from weaviate.proto.v1 import tenants_pb2, weaviate_pb2_grpc

        reply = tenants_pb2.TenantsGetReply()
        payload = reply.SerializeToString()

        def frame(p, flag=0x00):
            return struct.pack(">BI", flag, len(p)) + p

        body = frame(payload) + frame(b"grpc-status:0\\r\\n", 0x80)

        async def sender(url, headers, body_in, timeout):
            assert headers["authorization"] == "Bearer k"
            assert url.endswith("/weaviate.v1.Weaviate/TenantsGet")
            return 200, {}, body

        weaviate_grpc_web.set_sender(sender)
        from weaviate_grpc_web import GrpcWebChannel
        ch = GrpcWebChannel("localhost:50051", secure=False)
        stub = weaviate_pb2_grpc.WeaviateStub(ch)

        async def main():
            res = await stub.TenantsGet(
                tenants_pb2.TenantsGetRequest(),
                metadata=[("authorization", "Bearer k")],
                timeout=5,
            )
            assert isinstance(res, tenants_pb2.TenantsGetReply)
            print("OK")

        asyncio.run(main())
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout

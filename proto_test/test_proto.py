import importlib
from importlib.metadata import PackageNotFoundError, version as metadata_version

import pytest
from packaging import version


def test_proto_import():
    grpc_ver = version.parse(metadata_version("grpcio"))
    pb_ver = version.parse(metadata_version("protobuf"))

    if (pb_ver >= version.parse("6.30.0") and grpc_ver < version.parse("1.72.0")) or (
        pb_ver >= version.parse("5.26.1") and grpc_ver < version.parse("1.63.0")
    ):
        with pytest.raises(Exception) as exc_info:
            import weaviate
        assert "gRPC incompatibility detected" in str(exc_info.value)
    else:
        import weaviate

        assert weaviate.version is not None


def test_grpcio_metadata_fallback_under_emscripten(monkeypatch):
    """Fall back for grpcio when its metadata is absent; protobuf still surfaces.

    Under Pyodide/Emscripten grpcio is excluded via an environment marker, so its
    distribution metadata is missing and ``get_version`` must fall back to a working
    proto variant; a genuinely missing protobuf is still surfaced, not masked.
    """
    mod = importlib.import_module("weaviate.proto.v1")

    def raises(pkg: str) -> str:
        raise PackageNotFoundError(pkg)

    monkeypatch.setattr(mod, "metadata_version", raises)

    assert str(mod.get_version("grpcio")) == "1.72.1"
    with pytest.raises(PackageNotFoundError):
        mod.get_version("protobuf")


def test_get_version_passthrough_when_installed(monkeypatch):
    """On a normal install the real version is returned unchanged (no fallback)."""
    mod = importlib.import_module("weaviate.proto.v1")
    monkeypatch.setattr(mod, "metadata_version", lambda pkg: "1.2.3")
    assert str(mod.get_version("grpcio")) == "1.2.3"
    assert str(mod.get_version("protobuf")) == "1.2.3"

import importlib
import pathlib
import re
from importlib.metadata import PackageNotFoundError, version as metadata_version

import pytest
from packaging import version


# CI installs incompatible grpcio/protobuf pairs; there weaviate.proto.v1 cannot import, so
# the tests below are skipped. This check imports nothing from weaviate.
def _versions_incompatible() -> bool:
    """Whether the installed grpcio/protobuf pair makes ``import weaviate.proto.v1`` raise."""
    try:
        grpc_ver = version.parse(metadata_version("grpcio"))
        pb_ver = version.parse(metadata_version("protobuf"))
    except PackageNotFoundError:
        return False
    return (pb_ver >= version.parse("6.30.0") and grpc_ver < version.parse("1.72.0")) or (
        pb_ver >= version.parse("5.26.1") and grpc_ver < version.parse("1.63.0")
    )


_skip_if_incompatible = pytest.mark.skipif(
    _versions_incompatible(),
    reason="incompatible grpcio/protobuf pair: weaviate.proto.v1 does not import",
)


def test_proto_import():
    grpc_ver = version.parse(metadata_version("grpcio"))
    pb_ver = version.parse(metadata_version("protobuf"))
    if (pb_ver >= version.parse("6.30.0") and grpc_ver < version.parse("1.72.0")) or (
        pb_ver >= version.parse("5.26.1") and grpc_ver < version.parse("1.63.0")
    ):
        with pytest.raises(Exception) as e:
            importlib.import_module("weaviate")
        assert "WeaviateProtobufIncompatibility" in str(e.type)
    else:
        import weaviate

        assert weaviate.version is not None


@_skip_if_incompatible
def test_grpcio_metadata_fallback_under_emscripten(monkeypatch):
    """Under Emscripten a missing grpcio falls back to _GRPCIO_FALLBACK_VERSION.

    A missing protobuf still raises.
    """
    mod = importlib.import_module("weaviate.proto.v1")

    def raises(pkg: str) -> str:
        raise PackageNotFoundError(pkg)

    monkeypatch.setattr(mod, "metadata_version", raises)
    monkeypatch.setattr("sys.platform", "emscripten")

    assert str(mod.get_version("grpcio")) == "1.72.1"
    with pytest.raises(PackageNotFoundError):
        mod.get_version("protobuf")


@_skip_if_incompatible
def test_grpcio_missing_metadata_raises_off_emscripten(monkeypatch):
    """Off Emscripten, missing grpcio metadata surfaces instead of being masked."""
    mod = importlib.import_module("weaviate.proto.v1")

    def raises(pkg: str) -> str:
        raise PackageNotFoundError(pkg)

    monkeypatch.setattr(mod, "metadata_version", raises)
    monkeypatch.setattr("sys.platform", "linux")
    with pytest.raises(PackageNotFoundError):
        mod.get_version("grpcio")


@_skip_if_incompatible
def test_grpcio_fallback_version_is_at_least_every_stub_generated_version():
    """_GRPCIO_FALLBACK_VERSION is at least every vendored stub's GRPC_GENERATED_VERSION."""
    try:
        from grpc._utilities import first_version_is_lower
    except ImportError:
        pytest.skip(
            "grpc._utilities.first_version_is_lower is unavailable in this grpcio; "
            "newer matrix cells run the comparison"
        )

    fallback = importlib.import_module("weaviate.proto.v1")._GRPCIO_FALLBACK_VERSION
    proto_root = pathlib.Path(__file__).resolve().parents[1] / "weaviate" / "proto" / "v1"
    stub_files = sorted(proto_root.glob("*/v1/*_pb2_grpc.py"))
    assert stub_files, "no vendored *_pb2_grpc.py stubs found"

    gate_pattern = re.compile(r"^GRPC_GENERATED_VERSION = '([^']+)'", re.MULTILINE)
    gated = 0
    for stub in stub_files:
        match = gate_pattern.search(stub.read_text())
        if match is None:
            continue  # older codegen (e.g. v4216) emits no version gate
        gated += 1
        generated = match.group(1)
        assert not first_version_is_lower(fallback, generated), (
            f"{stub.relative_to(proto_root)} was generated for grpcio {generated}, above "
            f"_GRPCIO_FALLBACK_VERSION {fallback}; bump it and the grpc shim's "
            "FAKE_GRPC_VERSION to match"
        )
    assert gated > 0, "no stub carried a GRPC_GENERATED_VERSION gate; check the extraction regex"


def test_shim_fake_grpc_version_matches_the_fallback():
    """The grpc shim's FAKE_GRPC_VERSION equals _GRPCIO_FALLBACK_VERSION.

    Read as text: weaviate_client_web imports pyodide, so it cannot be imported here.
    """
    repo = pathlib.Path(__file__).resolve().parents[1]

    def literal(path: pathlib.Path, name: str) -> str:
        match = re.search(rf'^{name} = "([^"]+)"', path.read_text(), re.MULTILINE)
        assert match is not None, f"{name} not found in {path}"
        return match.group(1)

    fallback = literal(
        repo / "weaviate" / "proto" / "v1" / "__init__.py", "_GRPCIO_FALLBACK_VERSION"
    )
    shim = repo / "packages" / "web" / "src" / "weaviate_client_web" / "_shim.py"
    assert literal(shim, "FAKE_GRPC_VERSION") == fallback

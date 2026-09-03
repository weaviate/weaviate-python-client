import pytest
from importlib.metadata import version as metadata_version
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

import pytest
import weaviate
from importlib.metadata import version as metadata_version
from packaging import version
from weaviate.exceptions import WeaviateProtobufIncompatibility


@pytest.mark.proto
def test_proto_import():
    grpc_ver = version.parse(metadata_version("grpcio"))
    pb_ver = version.parse(metadata_version("protobuf"))

    if (pb_ver >= version.parse("6.30.0") and grpc_ver < version.parse("1.72.0")) or (
        pb_ver >= version.parse("5.26.1") and grpc_ver < version.parse("1.63.0")
    ):
        with pytest.raises(WeaviateProtobufIncompatibility):
            with weaviate.connect_to_local() as client:
                client.get_meta()

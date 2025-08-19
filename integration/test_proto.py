import os
import pytest
import weaviate
from packaging import version
from weaviate.exceptions import WeaviateProtobufIncompatibility


@pytest.mark.proto
def test_proto_import():
    grpc_ver_env, pb_ver_env = os.environ.get("GRPC_VER"), os.environ.get("PB_VER")
    assert grpc_ver_env is not None, "GRPC_VER environment variable is not set"
    assert pb_ver_env is not None, "PB_VER environment variable is not set"

    grpc_ver = version.parse(grpc_ver_env)
    pb_ver = version.parse(pb_ver_env)

    if (pb_ver >= version.parse("6.30.0") and grpc_ver < version.parse("1.72.0")) or (
        pb_ver >= version.parse("5.26.1") and grpc_ver < version.parse("1.63.0")
    ):
        with pytest.raises(WeaviateProtobufIncompatibility):
            with weaviate.connect_to_local() as client:
                client.get_meta()

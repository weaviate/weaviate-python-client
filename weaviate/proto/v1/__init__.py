import warnings

import grpc_tools.grpc_version

warnings.filterwarnings(
    "ignore",
    r"(?=.*5\.27\.\d+)(?=.*5\.28\.\d+)(?=.*obsolete)",
    UserWarning,
    "google.protobuf.runtime_version",
)
# ref: https://github.com/grpc/grpc/issues/37609 and https://github.com/protocolbuffers/protobuf/pull/17241

import importlib
from packaging import version
import grpc_tools

def get_protobuf_version() -> version.Version:
    """Get the installed protobuf version."""
    return version.parse(grpc_tools.grpc_version.VERSION)


def get_protobuf_major_version():
    """Get the major version of installed protobuf (4 or 5)."""
    pb_version = get_protobuf_version()
    if pb_version >= version.parse("1.70.0"):
        return 6
    elif pb_version >= version.parse("1.60.0"):
        return 5
    elif pb_version >= version.parse("1.50.0"):
        return 4
    else:
        raise RuntimeError(f"Unsupported grpcio-tools version: {pb_version}. Only versions 1.50.0+ and <1.80 are supported.")

if get_protobuf_major_version() == 5:
    from weaviate.proto.v1.v5.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, properties_pb2, search_get_pb2, tenants_pb2
else:
    from weaviate.proto.v1.v4.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, properties_pb2, search_get_pb2, tenants_pb2

__all__ = [
    "aggregate_pb2", "base_pb2", "base_search_pb2", "batch_delete_pb2", "batch_pb2", "generative_pb2", "properties_pb2", "search_get_pb2", "tenants_pb2", "weaviate_pb2_grpc"
]
import warnings


warnings.filterwarnings(
    "ignore",
    r"(?=.*5\.27\.\d+)(?=.*5\.28\.\d+)(?=.*obsolete)",
    UserWarning,
    "google.protobuf.runtime_version",
)
# ref: https://github.com/grpc/grpc/issues/37609 and https://github.com/protocolbuffers/protobuf/pull/17241

from packaging import version

from importlib.metadata import version as metadata_version

def get_protobuf_version() -> version.Version:
    """Get the installed protobuf version."""
    return version.parse(metadata_version('grpcio'))


pb_version = get_protobuf_version()
if pb_version >= version.parse("1.70.0"):
    from weaviate.proto.v1.v6.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("1.66.2"):
    from weaviate.proto.v1.v52.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("1.60.0"):
    from weaviate.proto.v1.v51.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("1.50.0"):
    from weaviate.proto.v1.v4.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, properties_pb2, search_get_pb2, tenants_pb2
else:
    raise RuntimeError(f"Unsupported grpcio-tools version: {pb_version}. Only versions 1.50.0+ and <1.80 are supported.")

__all__ = [
    "aggregate_pb2", "base_pb2", "base_search_pb2", "batch_delete_pb2", "batch_pb2", "generative_pb2", "properties_pb2", "search_get_pb2", "tenants_pb2", "weaviate_pb2_grpc"
]
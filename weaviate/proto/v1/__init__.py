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

from weaviate.exceptions import WeaviateProtobufIncompatibility

def get_version(pkg: str)-> version.Version:
    return version.parse(metadata_version(pkg))

pb_version, grpc_version = get_version("protobuf"), get_version("grpcio")
if pb_version >= version.parse("6.30.0"):
    if grpc_version < version.parse("1.72.0"):
        raise WeaviateProtobufIncompatibility(pb_version, grpc_version)
    from weaviate.proto.v1.v6300.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, health_pb2, health_pb2_grpc, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("5.26.1"):
    if grpc_version < version.parse("1.63.0"):
        raise WeaviateProtobufIncompatibility(pb_version, grpc_version)
    from weaviate.proto.v1.v5261.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, health_pb2, health_pb2_grpc, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("4.21.6"):
    from weaviate.proto.v1.v4216.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, health_pb2, health_pb2_grpc, properties_pb2, search_get_pb2, tenants_pb2
else:
    raise RuntimeError(f"Unsupported protobuf version: {pb_version}. Only versions 4.21.6+ are supported.")

__all__ = [
    "aggregate_pb2", "base_pb2", "base_search_pb2", "batch_delete_pb2", "batch_pb2", "generative_pb2", "health_pb2", "health_pb2_grpc", "properties_pb2", "search_get_pb2", "tenants_pb2", "weaviate_pb2_grpc"
]
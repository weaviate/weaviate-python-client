import warnings


warnings.filterwarnings(
    "ignore",
    r"(?=.*5\.27\.\d+)(?=.*5\.28\.\d+)(?=.*obsolete)",
    UserWarning,
    "google.protobuf.runtime_version",
)
# ref: https://github.com/grpc/grpc/issues/37609 and https://github.com/protocolbuffers/protobuf/pull/17241

from packaging import version

from importlib.metadata import PackageNotFoundError, version as metadata_version

from weaviate.exceptions import WeaviateProtobufIncompatibility

# Fallback grpcio version used only when grpcio is not installed as a distribution.
# This happens under Pyodide/Emscripten, where grpcio has no wheel and is excluded
# via the `sys_platform != "emscripten"` marker in setup.cfg; the grpc module itself
# is provided there by a pure-Python shim (see the weaviate-python-grpc-web package).
# On every normal install grpcio's metadata is present and the real version is used,
# so this branch is not taken. Restricted to grpcio so that a genuinely missing
# protobuf (which is required and pure-Python under Pyodide) is never masked.
_GRPCIO_FALLBACK_VERSION = "1.72.1"

def get_version(pkg: str) -> version.Version:
    try:
        return version.parse(metadata_version(pkg))
    except PackageNotFoundError:
        if pkg == "grpcio":
            return version.parse(_GRPCIO_FALLBACK_VERSION)
        raise

pb_version, grpc_version = get_version("protobuf"), get_version("grpcio")
if pb_version >= version.parse("6.30.0"):
    if grpc_version < version.parse("1.72.0"):
        raise WeaviateProtobufIncompatibility(pb_version, grpc_version)
    from weaviate.proto.v1.v6300.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, health_weaviate_pb2, health_weaviate_pb2_grpc, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("5.26.1"):
    if grpc_version < version.parse("1.63.0"):
        raise WeaviateProtobufIncompatibility(pb_version, grpc_version)
    from weaviate.proto.v1.v5261.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, health_weaviate_pb2, health_weaviate_pb2_grpc, properties_pb2, search_get_pb2, tenants_pb2
elif pb_version >= version.parse("4.21.6"):
    from weaviate.proto.v1.v4216.v1 import weaviate_pb2_grpc, aggregate_pb2, base_pb2, base_search_pb2, batch_delete_pb2, batch_pb2, generative_pb2, health_weaviate_pb2, health_weaviate_pb2_grpc, properties_pb2, search_get_pb2, tenants_pb2
else:
    raise RuntimeError(f"Unsupported protobuf version: {pb_version}. Only versions 4.21.6+ are supported.")

__all__ = [
    "aggregate_pb2", "base_pb2", "base_search_pb2", "batch_delete_pb2", "batch_pb2", "generative_pb2", "health_weaviate_pb2", "health_weaviate_pb2_grpc", "properties_pb2", "search_get_pb2", "tenants_pb2", "weaviate_pb2_grpc"
]
import warnings

warnings.filterwarnings(
    "ignore",
    r"(?=.*5\.27\.\d+)(?=.*5\.28\.\d+)(?=.*obsolete)",
    UserWarning,
    "google.protobuf.runtime_version",
)
# ref: https://github.com/grpc/grpc/issues/37609 and https://github.com/protocolbuffers/protobuf/pull/17241

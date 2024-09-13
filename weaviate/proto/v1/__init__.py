import warnings
warnings.filterwarnings("ignore", ".*obsolete", UserWarning, "google.protobuf.runtime_version")
# copied from https://github.com/grpc/grpc/issues/37609#issuecomment-2328376837 to handle https://github.com/protocolbuffers/protobuf/pull/17241
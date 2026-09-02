import pytest
from importlib.metadata import version as metadata_version
from packaging import version


def _installed_protobuf_and_grpc_are_incompatible() -> bool:
    grpc_ver = version.parse(metadata_version("grpcio"))
    pb_ver = version.parse(metadata_version("protobuf"))

    return (pb_ver >= version.parse("6.30.0") and grpc_ver < version.parse("1.72.0")) or (
        pb_ver >= version.parse("5.26.1") and grpc_ver < version.parse("1.63.0")
    )


def test_proto_import():
    if _installed_protobuf_and_grpc_are_incompatible():
        with pytest.raises(Exception) as exc_info:
            import weaviate
        assert exc_info.type.__name__ == "WeaviateProtobufIncompatibility"
        assert "gRPC incompatibility detected" in str(exc_info.value)
    else:
        import weaviate

        assert weaviate.version is not None


def test_generative_digitalocean_and_meta_protos_are_available():
    if _installed_protobuf_and_grpc_are_incompatible():
        pytest.skip("installed protobuf and grpcio versions are intentionally incompatible")

    from weaviate.proto.v1 import generative_pb2

    provider_fields = generative_pb2.GenerativeProvider.DESCRIPTOR.fields_by_name
    metadata_fields = generative_pb2.GenerativeMetadata.DESCRIPTOR.fields_by_name

    assert provider_fields["digitalocean"].message_type.full_name == (
        "weaviate.v1.GenerativeDigitalOcean"
    )
    assert provider_fields["digitalocean"].number == 17
    assert provider_fields["meta"].message_type.full_name == "weaviate.v1.GenerativeMeta"
    assert provider_fields["meta"].number == 18
    assert metadata_fields["digitalocean"].message_type.full_name == (
        "weaviate.v1.GenerativeDigitalOceanMetadata"
    )
    assert metadata_fields["digitalocean"].number == 15
    assert metadata_fields["meta"].message_type.full_name == ("weaviate.v1.GenerativeMetaMetadata")
    assert metadata_fields["meta"].number == 16

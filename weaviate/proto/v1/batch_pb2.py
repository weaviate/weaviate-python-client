# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: v1/batch.proto
# Protobuf Python Version: 5.27.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder

_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC, 5, 27, 2, "", "v1/batch.proto"
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2
from weaviate.proto.v1 import base_pb2 as v1_dot_base__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\x0ev1/batch.proto\x12\x0bweaviate.v1\x1a\x1cgoogle/protobuf/struct.proto\x1a\rv1/base.proto"\x1f\n\x0f\x42\x61tchWriteReply\x12\x0c\n\x04took\x18\x01 \x01(\x02"\x12\n\x10\x42\x61tchReadRequest"\x95\x01\n\x13\x42\x61tchObjectsRequest\x12)\n\x07objects\x18\x01 \x03(\x0b\x32\x18.weaviate.v1.BatchObject\x12=\n\x11\x63onsistency_level\x18\x02 \x01(\x0e\x32\x1d.weaviate.v1.ConsistencyLevelH\x00\x88\x01\x01\x42\x14\n\x12_consistency_level"\x8b\x01\n\nBatchStart\x12=\n\x11\x63onsistency_level\x18\x01 \x01(\x0e\x32\x1d.weaviate.v1.ConsistencyLevelH\x00\x88\x01\x01\x12\x18\n\x0b\x63oncurrency\x18\x02 \x01(\x05H\x01\x88\x01\x01\x42\x14\n\x12_consistency_levelB\x0e\n\x0c_concurrency"\x0b\n\tBatchStop"\xa3\x01\n\x0c\x42\x61tchMessage\x12\'\n\x04init\x18\x01 \x01(\x0b\x32\x17.weaviate.v1.BatchStartH\x00\x12\x33\n\x07request\x18\x02 \x01(\x0b\x32 .weaviate.v1.BatchObjectsRequestH\x00\x12*\n\x08sentinel\x18\x03 \x01(\x0b\x32\x16.weaviate.v1.BatchStopH\x00\x42\t\n\x07message"\xde\x07\n\x0b\x42\x61tchObject\x12\x0c\n\x04uuid\x18\x01 \x01(\t\x12\x12\n\x06vector\x18\x02 \x03(\x02\x42\x02\x18\x01\x12\x37\n\nproperties\x18\x03 \x01(\x0b\x32#.weaviate.v1.BatchObject.Properties\x12\x12\n\ncollection\x18\x04 \x01(\t\x12\x0e\n\x06tenant\x18\x05 \x01(\t\x12\x14\n\x0cvector_bytes\x18\x06 \x01(\x0c\x12%\n\x07vectors\x18\x17 \x03(\x0b\x32\x14.weaviate.v1.Vectors\x1a\x84\x05\n\nProperties\x12\x33\n\x12non_ref_properties\x18\x01 \x01(\x0b\x32\x17.google.protobuf.Struct\x12N\n\x17single_target_ref_props\x18\x02 \x03(\x0b\x32-.weaviate.v1.BatchObject.SingleTargetRefProps\x12L\n\x16multi_target_ref_props\x18\x03 \x03(\x0b\x32,.weaviate.v1.BatchObject.MultiTargetRefProps\x12\x43\n\x17number_array_properties\x18\x04 \x03(\x0b\x32".weaviate.v1.NumberArrayProperties\x12=\n\x14int_array_properties\x18\x05 \x03(\x0b\x32\x1f.weaviate.v1.IntArrayProperties\x12?\n\x15text_array_properties\x18\x06 \x03(\x0b\x32 .weaviate.v1.TextArrayProperties\x12\x45\n\x18\x62oolean_array_properties\x18\x07 \x03(\x0b\x32#.weaviate.v1.BooleanArrayProperties\x12\x38\n\x11object_properties\x18\x08 \x03(\x0b\x32\x1d.weaviate.v1.ObjectProperties\x12\x43\n\x17object_array_properties\x18\t \x03(\x0b\x32".weaviate.v1.ObjectArrayProperties\x12\x18\n\x10\x65mpty_list_props\x18\n \x03(\t\x1a\x38\n\x14SingleTargetRefProps\x12\r\n\x05uuids\x18\x01 \x03(\t\x12\x11\n\tprop_name\x18\x02 \x01(\t\x1aR\n\x13MultiTargetRefProps\x12\r\n\x05uuids\x18\x01 \x03(\t\x12\x11\n\tprop_name\x18\x02 \x01(\t\x12\x19\n\x11target_collection\x18\x03 \x01(\t"*\n\nBatchError\x12\r\n\x05index\x18\x01 \x01(\x05\x12\r\n\x05\x65rror\x18\x02 \x01(\t"\x88\x01\n\x11\x42\x61tchObjectsReply\x12\x0c\n\x04took\x18\x01 \x01(\x02\x12\x39\n\x06\x65rrors\x18\x02 \x03(\x0b\x32).weaviate.v1.BatchObjectsReply.BatchError\x1a*\n\nBatchError\x12\r\n\x05index\x18\x01 \x01(\x05\x12\r\n\x05\x65rror\x18\x02 \x01(\tBo\n#io.weaviate.client.grpc.protocol.v1B\x12WeaviateProtoBatchZ4github.com/weaviate/weaviate/grpc/generated;protocolb\x06proto3'
)

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, "v1.batch_pb2", _globals)
if not _descriptor._USE_C_DESCRIPTORS:
    _globals["DESCRIPTOR"]._loaded_options = None
    _globals["DESCRIPTOR"]._serialized_options = (
        b"\n#io.weaviate.client.grpc.protocol.v1B\022WeaviateProtoBatchZ4github.com/weaviate/weaviate/grpc/generated;protocol"
    )
    _globals["_BATCHOBJECT"].fields_by_name["vector"]._loaded_options = None
    _globals["_BATCHOBJECT"].fields_by_name["vector"]._serialized_options = b"\030\001"
    _globals["_BATCHWRITEREPLY"]._serialized_start = 76
    _globals["_BATCHWRITEREPLY"]._serialized_end = 107
    _globals["_BATCHREADREQUEST"]._serialized_start = 109
    _globals["_BATCHREADREQUEST"]._serialized_end = 127
    _globals["_BATCHOBJECTSREQUEST"]._serialized_start = 130
    _globals["_BATCHOBJECTSREQUEST"]._serialized_end = 279
    _globals["_BATCHSTART"]._serialized_start = 282
    _globals["_BATCHSTART"]._serialized_end = 421
    _globals["_BATCHSTOP"]._serialized_start = 423
    _globals["_BATCHSTOP"]._serialized_end = 434
    _globals["_BATCHMESSAGE"]._serialized_start = 437
    _globals["_BATCHMESSAGE"]._serialized_end = 600
    _globals["_BATCHOBJECT"]._serialized_start = 603
    _globals["_BATCHOBJECT"]._serialized_end = 1593
    _globals["_BATCHOBJECT_PROPERTIES"]._serialized_start = 807
    _globals["_BATCHOBJECT_PROPERTIES"]._serialized_end = 1451
    _globals["_BATCHOBJECT_SINGLETARGETREFPROPS"]._serialized_start = 1453
    _globals["_BATCHOBJECT_SINGLETARGETREFPROPS"]._serialized_end = 1509
    _globals["_BATCHOBJECT_MULTITARGETREFPROPS"]._serialized_start = 1511
    _globals["_BATCHOBJECT_MULTITARGETREFPROPS"]._serialized_end = 1593
    _globals["_BATCHERROR"]._serialized_start = 1595
    _globals["_BATCHERROR"]._serialized_end = 1637
    _globals["_BATCHOBJECTSREPLY"]._serialized_start = 1640
    _globals["_BATCHOBJECTSREPLY"]._serialized_end = 1776
    _globals["_BATCHOBJECTSREPLY_BATCHERROR"]._serialized_start = 1595
    _globals["_BATCHOBJECTSREPLY_BATCHERROR"]._serialized_end = 1637
# @@protoc_insertion_point(module_scope)

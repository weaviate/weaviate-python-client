# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: v1/properties.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x13v1/properties.proto\x12\x0bweaviate.v1\"\x84\x01\n\nProperties\x12\x33\n\x06\x66ields\x18\x01 \x03(\x0b\x32#.weaviate.v1.Properties.FieldsEntry\x1a\x41\n\x0b\x46ieldsEntry\x12\x0b\n\x03key\x18\x01 \x01(\t\x12!\n\x05value\x18\x02 \x01(\x0b\x32\x12.weaviate.v1.Value:\x02\x38\x01\"\xa6\x02\n\x05Value\x12\x16\n\x0cnumber_value\x18\x01 \x01(\x01H\x00\x12\x16\n\x0cstring_value\x18\x02 \x01(\tH\x00\x12\x14\n\nbool_value\x18\x03 \x01(\x08H\x00\x12/\n\x0cobject_value\x18\x04 \x01(\x0b\x32\x17.weaviate.v1.PropertiesH\x00\x12,\n\nlist_value\x18\x05 \x01(\x0b\x32\x16.weaviate.v1.ListValueH\x00\x12\x14\n\ndate_value\x18\x06 \x01(\tH\x00\x12\x14\n\nuuid_value\x18\x07 \x01(\tH\x00\x12\x13\n\tint_value\x18\x08 \x01(\x03H\x00\x12/\n\tgeo_value\x18\t \x01(\x0b\x32\x1a.weaviate.v1.GeoCoordinateH\x00\x42\x06\n\x04kind\"/\n\tListValue\x12\"\n\x06values\x18\x01 \x03(\x0b\x32\x12.weaviate.v1.Value\"4\n\rGeoCoordinate\x12\x11\n\tlongitude\x18\x01 \x01(\x02\x12\x10\n\x08latitude\x18\x02 \x01(\x02\x42t\n#io.weaviate.client.grpc.protocol.v1B\x17WeaviateProtoPropertiesZ4github.com/weaviate/weaviate/grpc/generated;protocolb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'v1.properties_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  DESCRIPTOR._serialized_options = b'\n#io.weaviate.client.grpc.protocol.v1B\027WeaviateProtoPropertiesZ4github.com/weaviate/weaviate/grpc/generated;protocol'
  _PROPERTIES_FIELDSENTRY._options = None
  _PROPERTIES_FIELDSENTRY._serialized_options = b'8\001'
  _globals['_PROPERTIES']._serialized_start=37
  _globals['_PROPERTIES']._serialized_end=169
  _globals['_PROPERTIES_FIELDSENTRY']._serialized_start=104
  _globals['_PROPERTIES_FIELDSENTRY']._serialized_end=169
  _globals['_VALUE']._serialized_start=172
  _globals['_VALUE']._serialized_end=466
  _globals['_LISTVALUE']._serialized_start=468
  _globals['_LISTVALUE']._serialized_end=515
  _globals['_GEOCOORDINATE']._serialized_start=517
  _globals['_GEOCOORDINATE']._serialized_end=569
# @@protoc_insertion_point(module_scope)

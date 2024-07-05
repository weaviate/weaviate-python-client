from google.protobuf import struct_pb2 as _struct_pb2
from weaviate.proto.v1 import base_pb2 as _base_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class BatchObjectsRequest(_message.Message):
    __slots__ = ("objects", "consistency_level")
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    CONSISTENCY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    objects: _containers.RepeatedCompositeFieldContainer[BatchObject]
    consistency_level: _base_pb2.ConsistencyLevel
    def __init__(
        self,
        objects: _Optional[_Iterable[_Union[BatchObject, _Mapping]]] = ...,
        consistency_level: _Optional[_Union[_base_pb2.ConsistencyLevel, str]] = ...,
    ) -> None: ...

class BatchObject(_message.Message):
    __slots__ = ("uuid", "vector", "properties", "collection", "tenant", "vector_bytes", "vectors")

    class Properties(_message.Message):
        __slots__ = (
            "non_ref_properties",
            "single_target_ref_props",
            "multi_target_ref_props",
            "number_array_properties",
            "int_array_properties",
            "text_array_properties",
            "boolean_array_properties",
            "object_properties",
            "object_array_properties",
            "empty_list_props",
        )
        NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        SINGLE_TARGET_REF_PROPS_FIELD_NUMBER: _ClassVar[int]
        MULTI_TARGET_REF_PROPS_FIELD_NUMBER: _ClassVar[int]
        NUMBER_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        INT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        TEXT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        BOOLEAN_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        OBJECT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        EMPTY_LIST_PROPS_FIELD_NUMBER: _ClassVar[int]
        non_ref_properties: _struct_pb2.Struct
        single_target_ref_props: _containers.RepeatedCompositeFieldContainer[
            BatchObject.SingleTargetRefProps
        ]
        multi_target_ref_props: _containers.RepeatedCompositeFieldContainer[
            BatchObject.MultiTargetRefProps
        ]
        number_array_properties: _containers.RepeatedCompositeFieldContainer[
            _base_pb2.NumberArrayProperties
        ]
        int_array_properties: _containers.RepeatedCompositeFieldContainer[
            _base_pb2.IntArrayProperties
        ]
        text_array_properties: _containers.RepeatedCompositeFieldContainer[
            _base_pb2.TextArrayProperties
        ]
        boolean_array_properties: _containers.RepeatedCompositeFieldContainer[
            _base_pb2.BooleanArrayProperties
        ]
        object_properties: _containers.RepeatedCompositeFieldContainer[_base_pb2.ObjectProperties]
        object_array_properties: _containers.RepeatedCompositeFieldContainer[
            _base_pb2.ObjectArrayProperties
        ]
        empty_list_props: _containers.RepeatedScalarFieldContainer[str]
        def __init__(
            self,
            non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
            single_target_ref_props: _Optional[
                _Iterable[_Union[BatchObject.SingleTargetRefProps, _Mapping]]
            ] = ...,
            multi_target_ref_props: _Optional[
                _Iterable[_Union[BatchObject.MultiTargetRefProps, _Mapping]]
            ] = ...,
            number_array_properties: _Optional[
                _Iterable[_Union[_base_pb2.NumberArrayProperties, _Mapping]]
            ] = ...,
            int_array_properties: _Optional[
                _Iterable[_Union[_base_pb2.IntArrayProperties, _Mapping]]
            ] = ...,
            text_array_properties: _Optional[
                _Iterable[_Union[_base_pb2.TextArrayProperties, _Mapping]]
            ] = ...,
            boolean_array_properties: _Optional[
                _Iterable[_Union[_base_pb2.BooleanArrayProperties, _Mapping]]
            ] = ...,
            object_properties: _Optional[
                _Iterable[_Union[_base_pb2.ObjectProperties, _Mapping]]
            ] = ...,
            object_array_properties: _Optional[
                _Iterable[_Union[_base_pb2.ObjectArrayProperties, _Mapping]]
            ] = ...,
            empty_list_props: _Optional[_Iterable[str]] = ...,
        ) -> None: ...

    class SingleTargetRefProps(_message.Message):
        __slots__ = ("uuids", "prop_name")
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        PROP_NAME_FIELD_NUMBER: _ClassVar[int]
        uuids: _containers.RepeatedScalarFieldContainer[str]
        prop_name: str
        def __init__(
            self, uuids: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ...
        ) -> None: ...

    class MultiTargetRefProps(_message.Message):
        __slots__ = ("uuids", "prop_name", "target_collection")
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        PROP_NAME_FIELD_NUMBER: _ClassVar[int]
        TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
        uuids: _containers.RepeatedScalarFieldContainer[str]
        prop_name: str
        target_collection: str
        def __init__(
            self,
            uuids: _Optional[_Iterable[str]] = ...,
            prop_name: _Optional[str] = ...,
            target_collection: _Optional[str] = ...,
        ) -> None: ...
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    VECTOR_BYTES_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    vector: _containers.RepeatedScalarFieldContainer[float]
    properties: BatchObject.Properties
    collection: str
    tenant: str
    vector_bytes: bytes
    vectors: _containers.RepeatedCompositeFieldContainer[_base_pb2.Vectors]
    def __init__(
        self,
        uuid: _Optional[str] = ...,
        vector: _Optional[_Iterable[float]] = ...,
        properties: _Optional[_Union[BatchObject.Properties, _Mapping]] = ...,
        collection: _Optional[str] = ...,
        tenant: _Optional[str] = ...,
        vector_bytes: _Optional[bytes] = ...,
        vectors: _Optional[_Iterable[_Union[_base_pb2.Vectors, _Mapping]]] = ...,
    ) -> None: ...

class BatchObjectsReply(_message.Message):
    __slots__ = ("took", "errors")

    class BatchError(_message.Message):
        __slots__ = ("index", "error")
        INDEX_FIELD_NUMBER: _ClassVar[int]
        ERROR_FIELD_NUMBER: _ClassVar[int]
        index: int
        error: str
        def __init__(self, index: _Optional[int] = ..., error: _Optional[str] = ...) -> None: ...
    TOOK_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    took: float
    errors: _containers.RepeatedCompositeFieldContainer[BatchObjectsReply.BatchError]
    def __init__(
        self,
        took: _Optional[float] = ...,
        errors: _Optional[_Iterable[_Union[BatchObjectsReply.BatchError, _Mapping]]] = ...,
    ) -> None: ...

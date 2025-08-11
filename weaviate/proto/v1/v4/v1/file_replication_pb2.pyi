from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CompressionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
    COMPRESSION_TYPE_UNSPECIFIED: _ClassVar[CompressionType]
    COMPRESSION_TYPE_GZIP: _ClassVar[CompressionType]
    COMPRESSION_TYPE_ZLIB: _ClassVar[CompressionType]
    COMPRESSION_TYPE_DEFLATE: _ClassVar[CompressionType]
COMPRESSION_TYPE_UNSPECIFIED: CompressionType
COMPRESSION_TYPE_GZIP: CompressionType
COMPRESSION_TYPE_ZLIB: CompressionType
COMPRESSION_TYPE_DEFLATE: CompressionType

class PauseFileActivityRequest(_message.Message):
    __slots__ = ["index_name", "shard_name", "schema_version"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    SCHEMA_VERSION_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    schema_version: int
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ..., schema_version: _Optional[int] = ...) -> None: ...

class PauseFileActivityResponse(_message.Message):
    __slots__ = ["index_name", "shard_name"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ...) -> None: ...

class ResumeFileActivityRequest(_message.Message):
    __slots__ = ["index_name", "shard_name"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ...) -> None: ...

class ResumeFileActivityResponse(_message.Message):
    __slots__ = ["index_name", "shard_name"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ...) -> None: ...

class ListFilesRequest(_message.Message):
    __slots__ = ["index_name", "shard_name"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ...) -> None: ...

class ListFilesResponse(_message.Message):
    __slots__ = ["index_name", "shard_name", "file_names"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_NAMES_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    file_names: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ..., file_names: _Optional[_Iterable[str]] = ...) -> None: ...

class GetFileMetadataRequest(_message.Message):
    __slots__ = ["index_name", "shard_name", "file_name"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    file_name: str
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ..., file_name: _Optional[str] = ...) -> None: ...

class FileMetadata(_message.Message):
    __slots__ = ["index_name", "shard_name", "file_name", "size", "crc32"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    CRC32_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    file_name: str
    size: int
    crc32: int
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ..., file_name: _Optional[str] = ..., size: _Optional[int] = ..., crc32: _Optional[int] = ...) -> None: ...

class GetFileRequest(_message.Message):
    __slots__ = ["index_name", "shard_name", "file_name", "compression"]
    INDEX_NAME_FIELD_NUMBER: _ClassVar[int]
    SHARD_NAME_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    COMPRESSION_FIELD_NUMBER: _ClassVar[int]
    index_name: str
    shard_name: str
    file_name: str
    compression: CompressionType
    def __init__(self, index_name: _Optional[str] = ..., shard_name: _Optional[str] = ..., file_name: _Optional[str] = ..., compression: _Optional[_Union[CompressionType, str]] = ...) -> None: ...

class FileChunk(_message.Message):
    __slots__ = ["offset", "data", "eof"]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    EOF_FIELD_NUMBER: _ClassVar[int]
    offset: int
    data: bytes
    eof: bool
    def __init__(self, offset: _Optional[int] = ..., data: _Optional[bytes] = ..., eof: bool = ...) -> None: ...

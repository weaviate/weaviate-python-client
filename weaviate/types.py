import uuid
from dataclasses import dataclass, fields, Field
from enum import EnumMeta, Enum
from typing import Optional, List, Dict, Any, Tuple
from typing import Union


# MetaEnum and BaseEnum are required to support `in` statements:
#    'ALL' in ConsistencyLevel == True
#    12345 in ConsistencyLevel == False
class MetaEnum(EnumMeta):
    def __contains__(cls, item: Any) -> bool:
        try:
            # when item is type ConsistencyLevel
            return item.name in cls.__members__.keys()
        except AttributeError:
            # when item is type str
            return item in cls.__members__.keys()


class BaseEnum(Enum, metaclass=MetaEnum):
    pass


UUID = Union[str, uuid.UUID]
NUMBERS = Union[int, float]


class DataType(str, BaseEnum):
    TEXT = "text"
    TEXT_ARRAY = "text[]"
    INT = "int"
    INT_ARRAY = "int[]"
    BOOL = "boolean"
    BOOL_ARRAY = "boolean[]"
    NUMBER = "number"
    NUMBER_ARRAY = "number[]"
    DATE = "date"
    DATE_ARRAY = "date[]"
    UUID = "uuid"
    UUID_ARRAY = "uuid[]"
    GEO_COORDINATES = "geoCoordinates"
    BLOB = "blob"
    PHONE_NUMBER = "phoneNumber"


class VectorIndexType(str, BaseEnum):
    HNSW = "hnsw"


class Tokenization(str, BaseEnum):
    WORD = "word"
    WHITESPACE = "whitespace"
    LOWERCASE = "lowercase"
    FIELD = "field"


class Vectorizer(str, BaseEnum):
    NONE = "none"
    TEXT2VEC_OPENAI = "text2vec-openai"
    TEXT2VEC_COHERE = "text2vec-cohere"
    TEXT2VEC_PALM = "text2vec-palm"
    TEXT2VEC_HUGGINGFACE = "text2vec-huggingface"
    TEXT2VEC_TRANSFORMERS = "text2vec-transformers"
    TEXT2VEC_CONTEXTIONARY = "text2vec-contextionary"
    IMG2VEC_NEURAL = "img2vec-neural"
    MULTI2VEC_CLIP = "multi2vec-clip"
    REF2VEC_CENTROID = "ref2vec_centroid"


class VectorDistance(str, BaseEnum):
    COSINE = "cosine"
    DOT = "dot"
    L2_SQUARED = "l2-squared"
    HAMMING = "hamming"
    MANHATTAN = "manhattan"


class StopwordsPreset(str, BaseEnum):
    NONE = "none"
    EN = "en"


ModuleConfig = Dict[Vectorizer, Dict[str, Any]]


@dataclass
class BaseSchema:
    def to_dict(self) -> Dict[str, Any]:
        ret_dict = {}
        cls_fields: Tuple[Field, ...] = fields(self.__class__)
        for cls_field in cls_fields:
            val = getattr(self, cls_field.name)
            if val is None:
                continue
            if isinstance(val, Enum):
                ret_dict[cls_field.name] = str(val.value)
            else:
                ret_dict[cls_field.name] = val

        return ret_dict


@dataclass
class VectorIndexConfig(BaseSchema):
    distance: VectorDistance = VectorDistance.COSINE
    efConstruction: int = 128
    maxConnections: int = 64


@dataclass
class ShardingConfig(BaseSchema):
    virtualPerPhysical: Optional[int] = None
    desiredCount: Optional[int] = None
    actualCount: Optional[int] = None
    desiredVirtualCount: Optional[int] = None
    actualVirtualCount: Optional[int] = None
    key: Optional[str] = None
    strategy: Optional[str] = None
    function: Optional[str] = None


@dataclass
class ReplicationConfig(BaseSchema):
    factor: Optional[int] = None


@dataclass
class BM25config(BaseSchema):
    b: float = 0.75
    k1: float = 1.2


@dataclass
class Stopwords(BaseSchema):
    preset: StopwordsPreset = StopwordsPreset.EN
    additions: Optional[List[str]] = None
    removals: Optional[List[str]] = None


@dataclass
class InvertedIndexConfig(BaseSchema):
    bm25: Optional[BM25config] = None
    stopwords: Optional[Stopwords] = None
    indexTimestamps: bool = False
    indexPropertyLength: bool = False
    indexNullState: bool = False


@dataclass
class Property(BaseSchema):
    name: str
    dataType: DataType
    indexFilterable: Optional[bool] = None
    indexSearchable: Optional[bool] = None
    tokenization: Optional[Tokenization] = None
    description: Optional[str] = None
    moduleConfig: Optional[ModuleConfig] = None

    def to_dict(self):
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        return ret_dict


@dataclass
class Class:
    name: str
    properties: Optional[List[Property]] = None
    vectorIndexType: Optional[VectorIndexType] = None
    vectorizer: Optional[Vectorizer] = None
    vectorIndexConfig: Optional[VectorIndexConfig] = None
    description: Optional[str] = None
    shardingConfig: Optional[ShardingConfig] = None
    replicationConfig: Optional[ReplicationConfig] = None
    invertedIndexConfig: Optional[InvertedIndexConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = {"class": self.name}
        if self.properties is not None and len(self.properties) > 0:
            ret_dict["properties"] = [x.to_dict() for x in self.properties]

        cls_fields: Tuple[Field, ...] = fields(self.__class__)
        for cls_field in cls_fields:
            val = getattr(self, cls_field.name)
            if cls_field.name in ["name", "properties"] or val is None:
                continue
            if isinstance(val, Enum):
                ret_dict[cls_field.name] = str(val.value)
            elif isinstance(val, (bool, float, str, int)):
                ret_dict[cls_field.name] = str(val)
            else:
                ret_dict[cls_field.name] = val.to_dict()

        return ret_dict

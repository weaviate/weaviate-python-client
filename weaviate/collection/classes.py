import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import (
    Union,
    Dict,
    Any,
    Optional,
    List,
    Set,
    TypeVar,
    Type,
    Generic,
    get_args,
    get_origin,
    get_type_hints,
)

import uuid as uuid_package
from pydantic import BaseModel, Field, field_validator
from pydantic_core._pydantic_core import PydanticUndefined

from weaviate.util import _to_beacons, _capitalize_first_letter
from weaviate.weaviate_types import UUID, PYTHON_TYPE_TO_DATATYPE


@dataclass
class Error:
    code: int
    message: str


Errors = List[Error]


class DataType(str, Enum):
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


class VectorIndexType(str, Enum):
    HNSW = "hnsw"


class Tokenization(str, Enum):
    WORD = "word"
    WHITESPACE = "whitespace"
    LOWERCASE = "lowercase"
    FIELD = "field"


class Vectorizer(str, Enum):
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


class VectorDistance(str, Enum):
    COSINE = "cosine"
    DOT = "dot"
    L2_SQUARED = "l2-squared"
    HAMMING = "hamming"
    MANHATTAN = "manhattan"


class StopwordsPreset(str, Enum):
    NONE = "none"
    EN = "en"


ModuleConfig = Dict[Vectorizer, Dict[str, Any]]


class ConfigModel(BaseModel):
    def to_dict(self):
        return self.model_dump(exclude_none=True)


@dataclass
class VectorIndexConfig(ConfigModel):
    distance: VectorDistance = VectorDistance.COSINE
    efConstruction: int = 128
    maxConnections: int = 64


@dataclass
class ShardingConfig(ConfigModel):
    virtualPerPhysical: Optional[int] = None
    desiredCount: Optional[int] = None
    actualCount: Optional[int] = None
    desiredVirtualCount: Optional[int] = None
    actualVirtualCount: Optional[int] = None
    key: Optional[str] = None
    strategy: Optional[str] = None
    function: Optional[str] = None


class ReplicationConfig(ConfigModel):
    factor: Optional[int] = None


class BM25config(ConfigModel):
    b: float = 0.75
    k1: float = 1.2


class Stopwords(ConfigModel):
    preset: StopwordsPreset = StopwordsPreset.EN
    additions: Optional[List[str]] = None
    removals: Optional[List[str]] = None


class InvertedIndexConfig(ConfigModel):
    bm25: Optional[BM25config] = None
    stopwords: Optional[Stopwords] = None
    indexTimestamps: bool = False
    indexPropertyLength: bool = False
    indexNullState: bool = False


class MultiTenancyConfig(ConfigModel):
    enabled: bool = False


class CollectionConfigBase(ConfigModel):
    vectorIndexType: Optional[VectorIndexType] = None
    vectorizer: Optional[Vectorizer] = None
    vectorIndexConfig: Optional[VectorIndexConfig] = None
    description: Optional[str] = None
    shardingConfig: Optional[ShardingConfig] = None
    replicationConfig: Optional[ReplicationConfig] = None
    invertedIndexConfig: Optional[InvertedIndexConfig] = None
    multiTenancyConfig: Optional[MultiTenancyConfig] = None

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = {}

        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if cls_field in ["name", "model", "properties"] or val is None:
                continue
            if isinstance(val, Enum):
                ret_dict[cls_field] = str(val.value)
            elif isinstance(val, (bool, float, str, int)):
                ret_dict[cls_field] = str(val)
            else:
                assert isinstance(val, ConfigModel)
                ret_dict[cls_field] = val.to_dict()

        return ret_dict


class PropertyConfig(ConfigModel):
    indexFilterable: Optional[bool] = None
    indexSearchable: Optional[bool] = None
    tokenization: Optional[Tokenization] = None
    description: Optional[str] = None
    moduleConfig: Optional[ModuleConfig] = None


class Property(PropertyConfig, ConfigModel):
    name: str
    dataType: DataType

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        return ret_dict


class ReferenceProperty(ConfigModel):
    name: str
    reference_class_name: str

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ref_collection_name = self.reference_class_name[0].upper()
        if len(self.reference_class_name) > 1:
            ref_collection_name += self.reference_class_name[1:]
        ret_dict["dataType"] = [ref_collection_name]
        return ret_dict


class CollectionConfig(CollectionConfigBase):
    name: str
    properties: Optional[List[Union[Property, ReferenceProperty]]] = None

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()

        if self.name is not None:
            ret_dict["class"] = _capitalize_first_letter(self.name)

        if self.properties is not None:
            ret_dict["properties"] = [prop.to_dict() for prop in self.properties]

        return ret_dict


class MetadataGet(BaseModel):
    vector: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explain_score: bool = Field(alias="explainScore", default=False)
    is_consistent: bool = Field(alias="isConsistent", default=False)

    def _get_fields(self) -> Set[str]:
        additional_props: Set[str] = set()
        for field, value in self.model_fields.items():
            enabled: bool = getattr(self, field)
            if enabled:
                name = value.alias if value.alias is not None else field
                additional_props.add(name)
        return additional_props

    def to_graphql(self) -> str:
        additional_props = self._get_fields()
        if len(additional_props) > 0:
            return "_additional{" + " ".join(additional_props) + "}"
        else:
            return ""

    def to_rest(self) -> str:
        return ",".join(self._get_fields())


@dataclass
class _MetadataReturn:
    # uuid: Optional[uuid_package.UUID] = Field(None, alias="id")
    # vector: Optional[List[float]] = None
    # creation_time_unix: Optional[int] = Field(None, alias="creationTimeUnix")
    # last_update_time_unix: Optional[int] = Field(None, alias="lastUpdateTimeUnix")
    # distance: Optional[float] = None
    # certainty: Optional[float] = None
    # score: Optional[float] = None
    # explain_score: Optional[str] = Field(None, alias="explainScore")
    # is_consistent: Optional[bool] = Field(None, alias="isConsistent")
    uuid: Optional[uuid_package.UUID] = None
    vector: Optional[List[float]] = None
    creation_time_unix: Optional[int] = None
    last_update_time_unix: Optional[int] = None
    distance: Optional[float] = None
    certainty: Optional[float] = None
    score: Optional[float] = None
    explain_score: Optional[str] = None
    is_consistent: Optional[bool] = None

    def __init__(self, data: Optional[Dict[str, Any]] = None) -> None:
        if data is None:
            return

        def _to_uuid(uuid_str: Optional[str]) -> Optional[uuid_package.UUID]:
            if uuid_str is None:
                return None
            return uuid_package.UUID(hex=uuid_str)

        def _parse(key: str) -> Optional[Any]:
            return data.get(key)

        self.uuid = _to_uuid(_parse("id"))
        self.vector = _parse("vector")
        self.creation_time_unix = _parse("creationTimeUnix")
        self.last_update_time_unix = _parse("lastUpdateTimeUnix")
        self.distance = _parse("distance")
        self.certainty = _parse("certainty")
        self.score = _parse("score")
        self.explain_score = _parse("explainScore")
        self.is_consistent = _parse("isConsistent")


@dataclass
class RefToObject:
    uuids_to: Union[List[UUID], UUID]

    def to_beacon(self) -> List[Dict[str, str]]:
        return _to_beacons(self.uuids_to)


@dataclass
class PropertyConfig:
    indexFilterable: Optional[bool] = None
    indexSearchable: Optional[bool] = None
    tokenization: Optional[Tokenization] = None
    description: Optional[str] = None
    moduleConfig: Optional[ModuleConfig] = None

    # tmp solution. replace with a pydantic BaseModel, see bugreport: https://github.com/pydantic/pydantic/issues/6948
    def model_dump(self, exclude_unset: bool = True, exclude_none: bool = True) -> Dict[str, Any]:
        return {
            "indexFilterable": self.indexFilterable,
            "indexSearchable": self.indexSearchable,
            "tokenization": self.tokenization,
            "description": self.description,
            "moduleConfig": self.moduleConfig,
        }


@dataclass
class ReferenceTo:
    ref_type: Union[Type, str]

    @property
    def name(self) -> str:
        if isinstance(self.ref_type, type):
            return _capitalize_first_letter(self.ref_type.__name__)
        else:
            assert isinstance(self.ref_type, str)
            return _capitalize_first_letter(self.ref_type)


@dataclass
class BatchReference:
    from_uuid: UUID
    to_uuid: UUID


@dataclass
class DataObject:
    data: Dict[str, Any]
    uuid: Optional[UUID] = None
    vector: Optional[List[float]] = None


class BaseProperty(BaseModel):
    uuid: UUID = Field(default_factory=uuid_package.uuid4)
    vector: Optional[List[float]] = None

    # def __new__(cls, *args, **kwargs):
    #     #
    #     build = super().__new__(cls)
    #     # fields, class_vars = collect_model_fields(cls)
    #     for name, field in build.model_fields.items():
    #         if name not in BaseProperty.model_fields:
    #             field_type = build._remove_optional_type(field.annotation)
    #             if inspect.isclass(field_type):
    #                 if field.annotation not in PYTHON_TYPE_TO_DATATYPE:
    #                     build.model_fields[name] = fields.FieldInfo(annotation=typing.Optional[UUID], default=None)
    #
    #     build.__class_vars__.update(build.__class_vars__)
    #     return build
    #
    #
    # make references optional by default - does not work
    def __init__(self, **data) -> None:
        super().__init__(**data)
        self._reference_fields: Set[str] = self.get_ref_fields(type(self))

        self._reference_to_class: Dict[str, str] = {}
        for ref in self._reference_fields:
            self._reference_to_class[ref] = self.model_fields[ref].metadata[0].name

    @staticmethod
    def get_ref_fields(model: Type["BaseProperty"]) -> Set[str]:
        return {
            name
            for name, field in model.model_fields.items()
            if (
                field.metadata is not None
                and len(field.metadata) > 0
                and isinstance(field.metadata[0], ReferenceTo)
            )
            and name not in BaseProperty.model_fields
        }

    @staticmethod
    def get_non_ref_fields(model: Type["BaseProperty"]) -> Set[str]:
        return {
            name
            for name, field in model.model_fields.items()
            if (
                field.metadata is None
                or len(field.metadata) == 0
                or isinstance(field.metadata[0], PropertyConfig)
            )
            and name not in BaseProperty.model_fields
        }

    def props_to_dict(self, update: bool = False) -> Dict[str, Any]:
        fields_to_exclude: Set[str] = self._reference_fields.union({"uuid", "vector"})
        if update:
            fields_to_exclude.union(
                {field for field in self.model_fields.keys() if field not in self.model_fields_set}
            )

        c = self.model_dump(exclude=fields_to_exclude)
        for ref in self._reference_fields:
            val = getattr(self, ref, None)
            if val is not None:
                c[ref] = _to_beacons(val, self._reference_to_class[ref])
        return c

    @field_validator("uuid")
    def create_valid_uuid(cls, input_uuid: UUID) -> uuid_package.UUID:
        if isinstance(input_uuid, uuid_package.UUID):
            return input_uuid

        # see if str is already a valid uuid
        try:
            return uuid_package.UUID(input_uuid)
        except ValueError:
            hex_string = hashlib.md5(input_uuid.encode("UTF-8")).hexdigest()
            return uuid_package.UUID(hex=hex_string)

    @staticmethod
    def type_to_dict(model: Type["BaseProperty"]) -> List[Dict[str, Any]]:
        types = get_type_hints(model)

        non_optional_types = {
            name: BaseProperty._remove_optional_type(tt)
            for name, tt in types.items()
            if name not in BaseProperty.model_fields
        }

        non_ref_fields = model.get_non_ref_fields(model)
        properties = []
        for name in non_ref_fields:
            prop = {
                "name": _capitalize_first_letter(name),
                "dataType": [PYTHON_TYPE_TO_DATATYPE[non_optional_types[name]]],
            }
            metadata_list = model.model_fields[name].metadata
            if metadata_list is not None and len(metadata_list) > 0:
                metadata = metadata_list[0]
                if isinstance(metadata, PropertyConfig):
                    prop.update(metadata.model_dump(exclude_unset=True, exclude_none=True))

            properties.append(prop)

        reference_fields = model.get_ref_fields(model)
        properties.extend(
            {
                "name": _capitalize_first_letter(name),
                "dataType": [model.model_fields[name].metadata[0].name],
            }
            for name in reference_fields
        )

        return properties

    @staticmethod
    def get_non_optional_fields(model: Type["BaseProperty"]) -> Set[str]:
        return {
            field
            for field, val in model.model_fields.items()
            if val.default == PydanticUndefined and field not in BaseProperty.model_fields.keys()
        }

    @staticmethod
    def _remove_optional_type(python_type: type) -> type:
        is_list = get_origin(python_type) == list
        args = get_args(python_type)
        if len(args) == 0:
            return python_type

        return_type = [t for t in args if t is not None][0]

        if is_list:
            return List[return_type]
        else:
            return return_type


Model = TypeVar("Model", bound=BaseProperty)


class RefToObjectModel(BaseModel, Generic[Model]):
    uuids_to: Union[List[UUID], UUID] = Field()

    def to_beacon(self) -> List[Dict[str, str]]:
        return _to_beacons(self.uuids_to)


UserModelType = Type[BaseProperty]


class CollectionModelConfig(CollectionConfigBase, Generic[Model]):
    model: Type[Model]

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()

        ret_dict["class"] = _capitalize_first_letter(self.model.__name__)

        if self.model is not None:
            ret_dict["properties"] = self.model.type_to_dict(self.model)

        return ret_dict


class Tenant(BaseModel):
    name: str

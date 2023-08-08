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


class PQEncoderType(str, Enum):
    KMEANS = "kmeans"
    TILE = "tile"


class PQEncoderDistribution(str, Enum):
    LOG_NORMAL = "log-normal"
    NORMAL = "normal"


ModuleConfig = Dict[Vectorizer, Dict[str, Any]]


class ConfigCreateModel(BaseModel):
    def to_dict(self):
        return self.model_dump(exclude_none=True)


class ConfigUpdateModel(BaseModel):
    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        for cls_field in self.model_fields:
            val = getattr(self, cls_field)
            if val is None:
                continue
            if isinstance(val, Enum):
                schema[cls_field] = str(val.value)
            elif isinstance(val, (int, float, bool, str, list)):
                schema[cls_field] = val
            else:
                assert isinstance(val, ConfigUpdateModel)
                schema[cls_field] = val.merge_with_existing(schema[cls_field])
        return schema


class PQEncoderConfigCreate(ConfigCreateModel):
    type_: PQEncoderType = PQEncoderType.KMEANS
    distribution: PQEncoderDistribution = PQEncoderDistribution.LOG_NORMAL

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Must be done manually since Pydantic does not work well with type and type_.
        Errors shadowing type occur if we want to use type as a field name.
        """
        if self.type_ is not None:
            schema["type"] = str(self.type_.value)
        if self.distribution is not None:
            schema["distribution"] = str(self.distribution.value)
        return schema


class PQEncoderConfigUpdate(ConfigUpdateModel):
    type_: Optional[PQEncoderType] = None
    distribution: Optional[PQEncoderDistribution] = None

    def merge_with_existing(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Must be done manually since Pydantic does not work well with type and type_.
        Errors shadowing type occur if we want to use type as a field name.
        """
        if self.type_ is not None:
            schema["type"] = str(self.type_.value)
        if self.distribution is not None:
            schema["distribution"] = str(self.distribution.value)
        return schema


class PQConfigCreate(ConfigCreateModel):
    bitCompression: bool = Field(False, alias="bit_compression")
    centroids: int = 256
    enabled: bool = False
    segments: int = 0
    trainingLimit: int = Field(10000, alias="training_limit")
    encoder: PQEncoderConfigUpdate = PQEncoderConfigCreate()


class PQConfigUpdate(ConfigUpdateModel):
    bitCompression: Optional[bool] = Field(None, alias="bit_compression")
    centroids: Optional[int] = None
    enabled: Optional[bool] = None
    segments: Optional[int] = None
    trainingLimit: Optional[int] = Field(None, alias="training_limit")
    encoder: Optional[PQEncoderConfigUpdate] = None


class VectorIndexConfigCreate(ConfigCreateModel):
    cleanupIntervalSeconds: int = Field(300, alias="cleanup_interval_seconds")
    distance: VectorDistance = VectorDistance.COSINE
    dynamicEfMin: int = Field(100, alias="dynamic_ef_min")
    dynamicEfMax: int = Field(500, alias="dynamic_ef_max")
    dynamicEfFactor: int = Field(8, alias="dynamic_ef_factor")
    efConstruction: int = 128
    ef: int = -1
    efConstruction: int = Field(128, alias="ef_construction")
    flatSearchCutoff: int = Field(40000, alias="flat_search_cutoff")
    maxConnections: int = Field(64, alias="max_connections")
    pq: PQConfigCreate = PQConfigCreate()
    skip: bool = False
    vectorCacheMaxObjects: int = Field(1000000000000, alias="vector_cache_max_objects")


class VectorIndexConfigUpdate(ConfigUpdateModel):
    dynamicEfFactor: Optional[int] = Field(None, alias="dynamic_ef_factor")
    dynamicEfMin: Optional[int] = Field(None, alias="dynamic_ef_min")
    dynamicEfMax: Optional[int] = Field(None, alias="dynamic_ef_max")
    ef: Optional[int] = None
    flatSearchCutoff: Optional[int] = Field(None, alias="flat_search_cutoff")
    skip: Optional[bool] = None
    vectorCacheMaxObjects: Optional[int] = Field(None, alias="vector_cache_max_objects")
    pq: Optional[PQConfigUpdate] = None


class ShardingConfigCreate(ConfigCreateModel):
    virtualPerPhysical: int = Field(128, alias="virtual_per_physical")
    desiredCount: int = Field(1, alias="desired_count")
    actualCount: int = Field(1, alias="actual_count")
    desiredVirtualCount: int = Field(128, alias="desired_virtual_count")
    actualVirtualCount: int = Field(128, alias="actual_virtual_count")
    key: str = "_id"
    strategy: str = "hash"
    function: str = "murmur3"


class ReplicationConfigCreate(ConfigCreateModel):
    factor: int = 1


class ReplicationConfigUpdate(ConfigUpdateModel):
    factor: Optional[int] = None


class BM25ConfigCreate(ConfigCreateModel):
    b: float = 0.75
    k1: float = 1.2


class BM25ConfigUpdate(ConfigUpdateModel):
    b: Optional[float] = None
    k1: Optional[float] = None


class StopwordsCreate(ConfigCreateModel):
    preset: StopwordsPreset = StopwordsPreset.EN
    additions: Optional[List[str]] = None
    removals: Optional[List[str]] = None


class StopwordsUpdate(ConfigUpdateModel):
    preset: Optional[StopwordsPreset] = None
    additions: Optional[List[str]] = None
    removals: Optional[List[str]] = None


class InvertedIndexConfigCreate(ConfigCreateModel):
    bm25: BM25ConfigCreate = BM25ConfigCreate()
    cleanupIntervalSeconds: int = Field(60, alias="cleanup_interval_seconds")
    indexTimestamps: bool = Field(False, alias="index_timestamps")
    indexPropertyLength: bool = Field(False, alias="index_property_length")
    indexNullState: bool = Field(False, alias="index_null_state")
    stopwords: StopwordsCreate = StopwordsCreate()


class InvertedIndexConfigUpdate(ConfigUpdateModel):
    bm25: Optional[BM25ConfigUpdate] = None
    cleanupIntervalSeconds: Optional[int] = Field(None, alias="cleanup_interval_seconds")
    indexTimestamps: Optional[bool] = Field(None, alias="index_timestamps")
    indexPropertyLength: Optional[bool] = Field(None, alias="index_property_length")
    indexNullState: Optional[bool] = Field(None, alias="index_null_state")
    stopwords: Optional[StopwordsUpdate] = None


class MultiTenancyConfig(ConfigCreateModel):
    enabled: bool = False


class CollectionConfigCreateBase(ConfigCreateModel):
    description: Optional[str] = None
    invertedIndexConfig: Optional[InvertedIndexConfigCreate] = Field(
        None, alias="inverted_index_config"
    )
    multiTenancyConfig: Optional[MultiTenancyConfig] = Field(None, alias="multi_tenancy_config")
    replicationConfig: Optional[ReplicationConfigCreate] = Field(None, alias="replication_config")
    shardingConfig: Optional[ShardingConfigCreate] = Field(None, alias="sharding_config")
    vectorIndexConfig: Optional[VectorIndexConfigCreate] = Field(None, alias="vector_index_config")
    vectorIndexType: VectorIndexType = Field(VectorIndexType.HNSW, alias="vector_index_type")
    vectorizer: Vectorizer = Vectorizer.NONE

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
                assert isinstance(val, ConfigCreateModel)
                ret_dict[cls_field] = val.to_dict()

        return ret_dict


class CollectionConfigUpdate(ConfigUpdateModel):
    description: Optional[str] = None
    invertedIndexConfig: Optional[InvertedIndexConfigUpdate] = Field(
        None, alias="inverted_index_config"
    )
    replicationConfig: Optional[ReplicationConfigUpdate] = Field(None, alias="replication_config")
    vectorIndexConfig: Optional[VectorIndexConfigUpdate] = Field(None, alias="vector_index_config")


@dataclass
class _BM25Config:
    b: float
    k1: float


@dataclass
class _StopwordsConfig:
    preset: StopwordsPreset
    additions: Optional[List[str]]
    removals: Optional[List[str]]


@dataclass
class _InvertedIndexConfig:
    bm25: _BM25Config
    cleanup_interval_seconds: int
    stopwords: _StopwordsConfig


@dataclass
class _MultiTenancyConfig:
    enabled: bool


@dataclass
class _Property:
    data_type: str
    description: Optional[str]
    index_filterable: bool
    index_searchable: bool
    name: str
    tokenization: Optional[Tokenization]


@dataclass
class _ReplicationFactor:
    factor: int


@dataclass
class _ShardingConfig:
    virtual_per_physical: int
    desired_count: int
    actual_count: int
    desired_virtual_count: int
    actual_virtual_count: int
    key: str
    strategy: str
    function: str


@dataclass
class _PQEncoderConfig:
    type_: PQEncoderType
    distribution: PQEncoderDistribution


@dataclass
class _PQConfig:
    enabled: bool
    bit_compression: bool
    segments: int
    centroids: int
    training_limit: int
    encoder: _PQEncoderConfig


@dataclass
class _VectorIndexConfig:
    cleanup_interval_seconds: int
    distance: VectorDistance
    dynamic_ef_min: int
    dynamic_ef_max: int
    dynamic_ef_factor: int
    ef: int
    ef_construction: int
    flat_search_cutoff: int
    max_connections: int
    pq: _PQConfig
    skip: bool
    vector_cache_max_objects: int


@dataclass
class _CollectionConfig:
    name: str
    description: Optional[str]
    inverted_index_config: _InvertedIndexConfig
    multi_tenancy_config: _MultiTenancyConfig
    properties: List[_Property]
    replication_factor: _ReplicationFactor
    sharding_config: _ShardingConfig
    vector_index_config: _VectorIndexConfig
    vector_index_type: VectorIndexType
    vectorizer: Vectorizer


def _collection_config_from_json(schema: Dict[str, Any]) -> _CollectionConfig:
    return _CollectionConfig(
        name=schema["class"],
        description=schema.get("description"),
        inverted_index_config=_InvertedIndexConfig(
            bm25=_BM25Config(
                b=schema["invertedIndexConfig"]["bm25"]["b"],
                k1=schema["invertedIndexConfig"]["bm25"]["k1"],
            ),
            cleanup_interval_seconds=schema["invertedIndexConfig"]["cleanupIntervalSeconds"],
            stopwords=_StopwordsConfig(
                preset=StopwordsPreset(schema["invertedIndexConfig"]["stopwords"]["preset"]),
                additions=schema["invertedIndexConfig"]["stopwords"]["additions"],
                removals=schema["invertedIndexConfig"]["stopwords"]["removals"],
            ),
        ),
        multi_tenancy_config=_MultiTenancyConfig(enabled=schema["multiTenancyConfig"]["enabled"]),
        properties=[
            _Property(
                data_type=prop["dataType"][0],
                description=prop.get("description"),
                index_filterable=prop["indexFilterable"],
                index_searchable=prop["indexSearchable"],
                name=prop["name"],
                tokenization=Tokenization(prop["tokenization"])
                if prop.get("tokenization") is not None
                else None,
            )
            for prop in schema["properties"]
        ]
        if schema.get("properties") is not None
        else [],
        replication_factor=_ReplicationFactor(factor=schema["replicationConfig"]["factor"]),
        sharding_config=_ShardingConfig(
            virtual_per_physical=schema["shardingConfig"]["virtualPerPhysical"],
            desired_count=schema["shardingConfig"]["desiredCount"],
            actual_count=schema["shardingConfig"]["actualCount"],
            desired_virtual_count=schema["shardingConfig"]["desiredVirtualCount"],
            actual_virtual_count=schema["shardingConfig"]["actualVirtualCount"],
            key=schema["shardingConfig"]["key"],
            strategy=schema["shardingConfig"]["strategy"],
            function=schema["shardingConfig"]["function"],
        ),
        vector_index_config=_VectorIndexConfig(
            cleanup_interval_seconds=schema["vectorIndexConfig"]["cleanupIntervalSeconds"],
            distance=VectorDistance(schema["vectorIndexConfig"]["distance"]),
            dynamic_ef_min=schema["vectorIndexConfig"]["dynamicEfMin"],
            dynamic_ef_max=schema["vectorIndexConfig"]["dynamicEfMax"],
            dynamic_ef_factor=schema["vectorIndexConfig"]["dynamicEfFactor"],
            ef=schema["vectorIndexConfig"]["ef"],
            ef_construction=schema["vectorIndexConfig"]["efConstruction"],
            flat_search_cutoff=schema["vectorIndexConfig"]["flatSearchCutoff"],
            max_connections=schema["vectorIndexConfig"]["maxConnections"],
            pq=_PQConfig(
                enabled=schema["vectorIndexConfig"]["pq"]["enabled"],
                bit_compression=schema["vectorIndexConfig"]["pq"]["bitCompression"],
                segments=schema["vectorIndexConfig"]["pq"]["segments"],
                centroids=schema["vectorIndexConfig"]["pq"]["centroids"],
                training_limit=schema["vectorIndexConfig"]["pq"]["trainingLimit"],
                encoder=_PQEncoderConfig(
                    type_=PQEncoderType(schema["vectorIndexConfig"]["pq"]["encoder"]["type"]),
                    distribution=PQEncoderDistribution(
                        schema["vectorIndexConfig"]["pq"]["encoder"]["distribution"]
                    ),
                ),
            ),
            skip=schema["vectorIndexConfig"]["skip"],
            vector_cache_max_objects=schema["vectorIndexConfig"]["vectorCacheMaxObjects"],
        ),
        vector_index_type=VectorIndexType(schema["vectorIndexType"]),
        vectorizer=Vectorizer(schema["vectorizer"]),
    )


def _collection_configs_from_json(schema: Dict[str, Any]) -> Dict[str, _CollectionConfig]:
    return {schema["class"]: _collection_config_from_json(schema) for schema in schema["classes"]}


class PropertyConfig(ConfigCreateModel):
    indexFilterable: Optional[bool] = Field(None, alias="index_filterable")
    indexSearchable: Optional[bool] = Field(None, alias="index_searchable")
    tokenization: Optional[Tokenization] = None
    description: Optional[str] = None
    moduleConfig: Optional[ModuleConfig] = Field(None, alias="module_config")


class Property(PropertyConfig, ConfigCreateModel):
    name: str
    dataType: DataType = Field(..., alias="data_type")

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ret_dict["dataType"] = [ret_dict["dataType"]]
        return ret_dict


class ReferenceProperty(ConfigCreateModel):
    name: str
    reference_class_name: str

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()
        ref_collection_name = self.reference_class_name[0].upper()
        if len(self.reference_class_name) > 1:
            ref_collection_name += self.reference_class_name[1:]
        ret_dict["dataType"] = [ref_collection_name]
        return ret_dict


class CollectionConfig(CollectionConfigCreateBase):
    """Use this class when specifying all the configuration options relevant to your collection when using
    the non-ORM collections API. This class is a superset of the `CollectionConfigCreateBase` class, and
    includes all the options available to the `CollectionConfigCreateBase` class.

    When using this non-ORM API, you must specify the name and properties of the collection explicitly here.

    Example:
        ```python
        from weaviate.weaviate_classes as wvc

        config = wvc.CollectionConfig(
            name = "MyCollection",
            properties = [
                wvc.Property(
                    name="myProperty",
                    data_type=wvc.DataType.STRING,
                    index_searchable=True,
                    index_filterable=True,
                    description="A string property"
                )
            ]
        )
        ```
    """

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


def _metadata_from_dict(metadata: Dict[str, Any]) -> _MetadataReturn:
    return _MetadataReturn(
        uuid=uuid_package.UUID(metadata["id"]) if "id" in metadata else None,
        vector=metadata.get("vector"),
        creation_time_unix=metadata.get("creationTimeUnix"),
        last_update_time_unix=metadata.get("lastUpdateTimeUnix"),
        distance=metadata.get("distance"),
        certainty=metadata.get("certainty"),
        explain_score=metadata.get("explainScore"),
        score=metadata.get("score"),
        is_consistent=metadata.get("isConsistent"),
    )


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

    def model_post_init(self, __context: Any) -> None:
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
            name: BaseProperty.remove_optional_type(tt)
            for name, tt in types.items()
            if name not in BaseProperty.model_fields
        }

        non_ref_fields = model.get_non_ref_fields(model)
        properties = []
        for name in non_ref_fields:
            prop = {
                "name": name,
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
                "name": name,
                "dataType": [model.model_fields[name].metadata[0].name],
            }
            for name in reference_fields
        )

        return properties

    @staticmethod
    def get_non_default_fields(model: Type["BaseProperty"]) -> Set[str]:
        return {
            field
            for field, val in model.model_fields.items()
            if val.default == PydanticUndefined and field not in BaseProperty.model_fields.keys()
        }

    @staticmethod
    def remove_optional_type(python_type: type) -> type:
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


class CollectionModelConfig(CollectionConfigCreateBase, Generic[Model]):
    model: Type[Model]

    def to_dict(self) -> Dict[str, Any]:
        ret_dict = super().to_dict()

        ret_dict["class"] = _capitalize_first_letter(self.model.__name__)

        if self.model is not None:
            ret_dict["properties"] = self.model.type_to_dict(self.model)

        return ret_dict


class Tenant(BaseModel):
    name: str
